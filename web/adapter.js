/* Projeto Fio a Fio · versão 1.6
 * Adaptador entre o painel e o Supabase.
 *
 * O painel nasceu como artefato do Claude e usa a interface claude.use("db"),
 * claude.use("user"), claude.use("sample") e claude.use("downloads"). Este
 * arquivo implementa essa mesma interface sobre o Supabase e a API Python, para
 * que o código do painel continue igual.
 */
(function () {
  "use strict";
  var C = window.FIO_CONFIG || {};
  if (!window.supabase || !C.SUPABASE_URL) { console.error("Fio a Fio: configure web/config.js"); return; }
  var sb = window.supabase.createClient(C.SUPABASE_URL, C.SUPABASE_ANON_KEY, { auth: { persistSession: true, autoRefreshToken: true } });

  var TAB = { q1: "respostas_q1", q2: "respostas_q2", q3: "respostas_q3", codes: "codigos", cats: "categorias",
    cod: "codificacoes", sug: "sugestoes", temas: "temas_geradores", links: "links_online" };
  var ouvintes = {};
  function rid() { var a = crypto.getRandomValues(new Uint8Array(12)); return Array.from(a, function (x) { return (x % 36).toString(36); }).join(""); }
  function snap(row) { return { id: row.id, exists: true, data: function () { return row.data; }, metadata: { fromCache: false, hasPendingWrites: false } }; }
  function vazio(id) { return { id: id, exists: false, data: function () { return undefined; }, metadata: { fromCache: false, hasPendingWrites: false } }; }
  function erro(e) { var c = (e && e.code) === "42501" ? "invalid_argument" : (e && e.code) === "23505" ? "invalid_argument" : "unavailable"; return { code: c, message: (e && e.message) || String(e) }; }
  function tabela(nome) { var t = TAB[nome]; if (!t) throw new TypeError("Coleção desconhecida: " + nome); return t; }
  function recarregar(nome) { (ouvintes[nome] || []).forEach(function (f) { f(); }); }

  function docRef(nome, id) {
    var t = tabela(nome);
    return {
      id: id, path: nome + "/" + id,
      get: async function () { var r = await sb.from(t).select("id,data").eq("id", id).maybeSingle(); if (r.error) throw erro(r.error); return r.data ? snap(r.data) : vazio(id); },
      set: async function (d) { var r = await sb.from(t).upsert({ id: id, data: d }); if (r.error) throw erro(r.error); recarregar(nome); },
      update: async function (patch) {
        var a = await sb.from(t).select("data").eq("id", id).maybeSingle(); if (a.error) throw erro(a.error);
        if (!a.data) throw { code: "invalid_argument", message: "Documento não existe." };
        var r = await sb.from(t).update({ data: Object.assign({}, a.data.data, patch) }).eq("id", id); if (r.error) throw erro(r.error); recarregar(nome);
      },
      delete: async function () { var r = await sb.from(t).delete().eq("id", id); if (r.error) throw erro(r.error); recarregar(nome); },
      onSnapshot: function (next) { var self = this; var f = async function () { try { next(await self.get()); } catch (e) {} }; f(); return function () {}; },
      collection: function () { throw new TypeError("Subcoleções não são usadas."); }
    };
  }

  function colRef(nome) {
    var t = tabela(nome);
    return {
      path: nome,
      doc: function (id) { return docRef(nome, id || rid()); },
      add: async function (d) { var id = rid(); var r = await sb.from(t).insert({ id: id, data: d }); if (r.error) throw erro(r.error); recarregar(nome); return docRef(nome, id); },
      onSnapshot: function (next, onErr) {
        var vivo = true, timer = null;
        var carregar = async function () {
          var r = await sb.from(t).select("id,data").order("created_at");
          if (!vivo) return;
          if (r.error) { if (onErr) onErr(erro(r.error)); return; }
          var docs = r.data.map(snap);
          next({ docs: docs, size: docs.length, empty: !docs.length, docChanges: function () { return []; }, metadata: { fromCache: false, hasPendingWrites: false } });
        };
        (ouvintes[nome] = ouvintes[nome] || []).push(carregar);
        carregar();
        var canal = sb.channel("rt-" + t + "-" + rid())
          .on("postgres_changes", { event: "*", schema: "public", table: t }, function () { clearTimeout(timer); timer = setTimeout(carregar, 250); })
          .subscribe();
        var poll = setInterval(carregar, 30000);
        return function () { vivo = false; sb.removeChannel(canal); clearInterval(poll); };
      }
    };
  }

  var db = { collection: colRef, doc: function (p) { var s = p.split("/"); return docRef(s[0], s[1]); } };

  var perfil = null;
  async function carregarPerfil() {
    var u = (await sb.auth.getUser()).data.user;
    if (!u) { perfil = null; return null; }
    var r = await sb.from("perfis").select("id,papel,nome").eq("id", u.id).maybeSingle();
    perfil = r.data ? Object.assign({ email: u.email }, r.data) : null;
    return perfil;
  }

  var user = {
    id: async function () { var u = (await sb.auth.getUser()).data.user; return u ? u.id : null; },
    me: async function () { var p = perfil || await carregarPerfil(); return { id: p && p.id, name: (p && p.nome) || "", isOwner: !!p && p.papel === "admin", canEdit: !!p && p.papel === "admin" }; },
    profiles: async function (ids) {
      ids = [].concat(ids); var out = {};
      var r = await sb.from("perfis").select("id,nome").in("id", ids);
      (r.data || []).forEach(function (p) { out[p.id] = { id: p.id, name: p.nome || "" }; });
      ids.forEach(function (id) { if (!out[id]) out[id] = { id: id, name: "" }; });
      return out;
    },
    isOwner: async function () { var p = perfil || await carregarPerfil(); return !!p && p.papel === "admin"; },
    canEdit: async function () { var p = perfil || await carregarPerfil(); return !!p && p.papel === "admin"; }
  };

  async function api(caminho, corpo) {
    var s = (await sb.auth.getSession()).data.session;
    var r = await fetch(C.API_URL.replace(/\/$/, "") + caminho, {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: s ? "Bearer " + s.access_token : "" },
      body: JSON.stringify(corpo)
    });
    if (r.status === 429) throw { code: "rate_limited", message: "Muitas solicitações." };
    if (r.status === 401 || r.status === 403) throw { code: "not_granted", message: "Sem permissão." };
    if (!r.ok) { var t = ""; try { t = (await r.json()).detail; } catch (e) {} throw { code: "unavailable", message: t || ("Erro " + r.status) }; }
    return r.json();
  }

  var sample = async function (prompt, opts) {
    var r = await api("/api/claude", { prompt: typeof prompt === "string" ? prompt : prompt.map(function (m) { return m.content; }).join("\n\n") });
    if (opts && opts.onText) opts.onText({ text: r.text, delta: r.text });
    return { text: r.text, truncated: false, modelTierApplied: "default" };
  };
  sample.json = async function (prompt) { return (await api("/api/claude", { prompt: prompt, json: true })).json; };
  sample.limits = async function () { return { maxPromptBytes: 150000 }; };

  var downloads = {
    save: async function (req) {
      var blob = req.data instanceof Blob ? req.data : new Blob([req.data], { type: "text/plain;charset=utf-8" });
      var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = req.filename;
      document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
      return { status: "saved" };
    }
  };

  // Backup completo: todas as coleções, no formato que scripts/importar_artefato.py restaura.
  async function backup() {
    var out = { _meta: { projeto: "Fio a Fio", versao: (window.FIO_VERSAO || ""), geradoEm: new Date().toISOString() } };
    var nomes = Object.keys(TAB);
    for (var i = 0; i < nomes.length; i++) {
      var lista = [], de = 0;
      for (;;) {
        var r = await sb.from(TAB[nomes[i]]).select("id,data").order("id").range(de, de + 999);
        if (r.error) throw erro(r.error);
        r.data.forEach(function (x) { lista.push(Object.assign({ id: x.id }, x.data)); });
        if (r.data.length < 1000) break;
        de += 1000;
      }
      out[nomes[i]] = lista;
    }
    return out;
  }

  // Restauração: acrescenta e atualiza (upsert por id). Nunca apaga.
  async function restaurar(dados, progresso) {
    var feito = {};
    var nomes = Object.keys(TAB);
    for (var i = 0; i < nomes.length; i++) {
      var k = nomes[i], lista = dados[k];
      if (!Array.isArray(lista) || !lista.length) continue;
      var linhas = lista.filter(function (x) { return x && typeof x.id === "string" && x.id; }).map(function (x) {
        var d = Object.assign({}, x); delete d.id; return { id: x.id, data: d };
      });
      feito[k] = 0;
      for (var de = 0; de < linhas.length; de += 200) {
        var lote = linhas.slice(de, de + 200);
        var r = await sb.from(TAB[k]).upsert(lote, { onConflict: "id" });
        if (r.error) throw erro(r.error);
        feito[k] += lote.length;
        if (progresso) progresso(k, feito[k]);
      }
      recarregar(k);
    }
    return feito;
  }

  window.FIO = { backup: backup, restaurar: restaurar, sb: sb, api: api, cfg: C, carregarPerfil: carregarPerfil, perfil: function () { return perfil; },
    recarregarTudo: function () { Object.keys(ouvintes).forEach(recarregar); } };
  window.claude = { use: async function (n) { return { db: db, user: user, sample: sample, downloads: downloads }[n] || null; } };
})();
