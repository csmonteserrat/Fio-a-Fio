-- Projeto Fio a Fio · CS Monte Serrat · esquema do banco, versão 1.0
-- Rode no Supabase em SQL Editor > New query. Pode rodar de novo sem perder dados.
--
-- Modelo: cada coleção do painel é uma tabela com (id, data jsonb). As respostas
-- ficam em jsonb com os mesmos campos do questionário, o que mantém o site, a API
-- e os scripts de publicação lendo exatamente o mesmo formato.

-- ------------------------------------------------------------ perfis e papéis
create table if not exists public.perfis (
  id uuid primary key references auth.users on delete cascade,
  papel text not null check (papel in ('admin', 'avaliador')),
  nome text not null default '',
  criado_em timestamptz not null default now()
);
alter table public.perfis enable row level security;

create or replace function public.papel() returns text
language sql stable security definer set search_path = public as $$
  select papel from public.perfis where id = auth.uid()
$$;

drop policy if exists "perfil: ler o próprio ou admin" on public.perfis;
create policy "perfil: ler o próprio ou admin" on public.perfis
  for select using (id = auth.uid() or public.papel() = 'admin');

-- ------------------------------------------------------------ tabelas do painel
do $$
declare t text;
begin
  foreach t in array array['respostas_q1','respostas_q2','respostas_q3','codigos','categorias',
                           'codificacoes','sugestoes','temas_geradores','links_online'] loop
    execute format($f$
      create table if not exists public.%I (
        id text primary key default gen_random_uuid()::text,
        data jsonb not null default '{}'::jsonb,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now(),
        created_by uuid default auth.uid()
      );
      alter table public.%I enable row level security;
    $f$, t, t);
  end loop;
end $$;

create or replace function public.tocar_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

do $$
declare t text;
begin
  foreach t in array array['respostas_q1','respostas_q2','respostas_q3','codigos','categorias',
                           'codificacoes','sugestoes','temas_geradores','links_online'] loop
    execute format('drop trigger if exists tocar on public.%I', t);
    execute format('create trigger tocar before update on public.%I for each row execute function public.tocar_updated_at()', t);
  end loop;
end $$;

-- ------------------------------------------------------------ regras de acesso (RLS)
-- Respostas: avaliador e admin leem e incluem; só admin edita e exclui.
do $$
declare t text;
begin
  foreach t in array array['respostas_q1','respostas_q2','respostas_q3'] loop
    execute format('drop policy if exists "ler" on public.%I', t);
    execute format('drop policy if exists "incluir" on public.%I', t);
    execute format('drop policy if exists "editar" on public.%I', t);
    execute format('drop policy if exists "excluir" on public.%I', t);
    execute format($p$create policy "ler" on public.%I for select using (public.papel() in ('admin','avaliador'))$p$, t);
    execute format($p$create policy "incluir" on public.%I for insert with check (public.papel() in ('admin','avaliador'))$p$, t);
    execute format($p$create policy "editar" on public.%I for update using (public.papel() = 'admin')$p$, t);
    execute format($p$create policy "excluir" on public.%I for delete using (public.papel() = 'admin')$p$, t);
  end loop;
  -- Análise temática e links: só admin.
  foreach t in array array['codigos','categorias','codificacoes','sugestoes','temas_geradores','links_online'] loop
    execute format('drop policy if exists "admin" on public.%I', t);
    execute format($p$create policy "admin" on public.%I for all using (public.papel() = 'admin') with check (public.papel() = 'admin')$p$, t);
  end loop;
end $$;

-- ------------------------------------------------------------ Q3 online (sem login)
-- Quem recebe o link não tem conta. Essas duas funções são a única porta:
-- conferem o link e gravam a resposta, sem dar leitura a nenhuma tabela.
create or replace function public.link_online(tok text) returns json
language plpgsql stable security definer set search_path = public as $$
declare d jsonb;
begin
  select data into d from public.links_online where id = tok;
  if d is null then return json_build_object('valido', false); end if;
  return json_build_object('valido', true, 'resp', d->>'resp',
    'usado', coalesce((d->>'used')::boolean, false), 'geral', coalesce((d->>'geral')::boolean, false));
end $$;

create or replace function public.responder_online(tok text, respostas jsonb) returns text
language plpgsql volatile security definer set search_path = public as $$
declare d jsonb; geral boolean; quem text; prox int; codigo text;
begin
  select data into d from public.links_online where id = tok for update;
  if d is null then raise exception 'Este link não é válido.'; end if;
  geral := coalesce((d->>'geral')::boolean, false);
  if not geral and coalesce((d->>'used')::boolean, false) then raise exception 'Este link já foi usado.'; end if;
  quem := case when geral then nullif(trim(respostas->>'resp'), '') else d->>'resp' end;
  if quem is null then raise exception 'Selecione seu nome.'; end if;
  if quem <> 'Prefere não se identificar' and exists (
       select 1 from public.respostas_q3 where lower(data->>'resp') = lower(quem)) then
    raise exception '% já respondeu. Obrigado!', quem;
  end if;
  select coalesce(max(nullif(regexp_replace(data->>'code', '\D', '', 'g'), '')::int), 0) + 1
    into prox from public.respostas_q3;
  codigo := 'E' || lpad(prox::text, 2, '0');
  insert into public.respostas_q3 (data, created_by) values (
    (respostas - 'code' - 'aplicador') || jsonb_build_object('resp', quem, 'code', codigo,
      'aplicador', 'Online (autopreenchimento)', 'via', 'online',
      'createdAt', now(), 'updatedAt', now()), null);
  if not geral then
    update public.links_online set data = data || jsonb_build_object('used', true, 'usedAt', now()) where id = tok;
  end if;
  return codigo;
end $$;

revoke all on function public.link_online(text) from public;
revoke all on function public.responder_online(text, jsonb) from public;
grant execute on function public.link_online(text) to anon, authenticated;
grant execute on function public.responder_online(text, jsonb) to anon, authenticated;

-- ------------------------------------------------------------ tempo real
do $$
declare t text;
begin
  foreach t in array array['respostas_q1','respostas_q2','respostas_q3','codigos','categorias',
                           'codificacoes','sugestoes','temas_geradores','links_online'] loop
    begin
      execute format('alter publication supabase_realtime add table public.%I', t);
    exception when duplicate_object then null;
    end;
  end loop;
end $$;

-- ------------------------------------------------------------ usuários (rode depois de criá-los)
-- 1. Em Authentication > Users > Add user, crie:
--      seu e-mail de administrador (e de outros administradores, se houver)
--      avaliador@fioafio.app  (conta única dos avaliadores; e-mail fictício serve)
-- 2. Rode, trocando os e-mails:
-- insert into public.perfis (id, papel, nome)
--   select id, 'admin', 'Caio' from auth.users where email = 'SEU-EMAIL@exemplo.com'
--   on conflict (id) do update set papel = excluded.papel, nome = excluded.nome;
-- insert into public.perfis (id, papel, nome)
--   select id, 'avaliador', 'Avaliadores' from auth.users where email = 'avaliador@fioafio.app'
--   on conflict (id) do update set papel = excluded.papel, nome = excluded.nome;
