(() => {
  const lerJSON = (id) => JSON.parse(document.getElementById(id).textContent);

  async function postJSON(url, corpo) {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo ?? {}),
    });
    return { ok: resp.ok, dados: await resp.json() };
  }

  function ligarModal(modal) {
    const fechar = () => { modal.hidden = true; };
    modal.querySelectorAll("[data-fechar]").forEach((el) => el.addEventListener("click", fechar));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal.hidden) fechar();
    });
  }

  // ---------- Abas ----------
  const abas = document.querySelectorAll("[data-aba]");
  function mostrarAba(nome) {
    abas.forEach((aba) => {
      const ativa = aba.dataset.aba === nome;
      aba.classList.toggle("ativa", ativa);
      aba.setAttribute("aria-selected", String(ativa));
      document.getElementById(`aba-${aba.dataset.aba}`).hidden = !ativa;
    });
    if (nome === "colecao") carregarColecao();
  }

  abas.forEach((aba) => aba.addEventListener("click", () => mostrarAba(aba.dataset.aba)));

  // ---------- Crescimento (Vaso) ----------
  const botaoPlanta = document.getElementById("planta");
  const img = document.getElementById("estagio-img");
  const contador = document.getElementById("contador-estagio");
  const nome = document.getElementById("nome-estagio");
  const descricao = document.getElementById("descricao-estagio");
  const barra = document.getElementById("barra-progresso");
  const preenchida = document.getElementById("barra-preenchida");
  const textoProgresso = document.getElementById("texto-progresso");

  let estado = lerJSON("estado-inicial");

  function renderizarPlantio(novo, avancou = false) {
    estado = novo;
    contador.textContent = `Estágio ${estado.estagio_indice + 1} de ${estado.total_estagios}`;
    nome.textContent = estado.estagio.nome;
    descricao.textContent = estado.estagio.descricao;
    img.src = estado.estagio.imagem;
    img.alt = estado.estagio.nome;

    preenchida.style.width = `${(estado.progresso / estado.necessario) * 100}%`;
    barra.setAttribute("aria-valuemax", String(estado.necessario));
    barra.setAttribute("aria-valuenow", String(estado.progresso));
    textoProgresso.textContent = `${estado.progresso} / ${estado.necessario}`;

    if (avancou) {
      botaoPlanta.classList.remove("cresceu");
      void botaoPlanta.offsetWidth; // reinicia a animação
      botaoPlanta.classList.add("cresceu");
    }
  }

  function mostrarGota(evento) {
    const gota = document.createElement("span");
    gota.className = "gota";
    gota.textContent = "+1 💧";
    gota.style.left = `${evento.clientX}px`;
    gota.style.top = `${evento.clientY}px`;
    document.body.appendChild(gota);
    gota.addEventListener("animationend", () => gota.remove());
  }

  async function regar() {
    const { ok, dados } = await postJSON("/api/plantio/acao", { acao: "regar" });
    renderizarPlantio(dados.estado, ok && dados.avancou);
    if (ok && dados.nova_arvore) {
      avisar("🌳 Seu açaizeiro começou a produzir frutos e foi para a Coleção! Uma nova semente foi plantada no vaso.");
      mostrarAba("colecao");
    }
  }

  // Os cliques são enviados um de cada vez, em ordem, para o servidor
  // nunca receber duas ações sobre o mesmo estado ao mesmo tempo.
  let fila = Promise.resolve();
  botaoPlanta.addEventListener("click", (evento) => {
    mostrarGota(evento);
    fila = fila.then(regar).catch((err) => console.error(err));
  });

  renderizarPlantio(estado);

  // ---------- Coleção e colheita ----------
  const grade = document.getElementById("grade-arvores");
  const modelo = document.getElementById("modelo-arvore");
  const vazia = document.getElementById("colecao-vazia");
  const aviso = document.getElementById("aviso-colecao");
  const selo = document.getElementById("selo-colecao");
  const moedas = document.getElementById("moedas");
  const totalColheitas = document.getElementById("total-colheitas");
  const modalColheita = document.getElementById("modal-colheita");
  ligarModal(modalColheita);

  let colecao = lerJSON("colecao-inicial");
  let recarregando = false;

  function avisar(texto, erro = false) {
    aviso.textContent = texto;
    aviso.classList.toggle("erro", erro);
    aviso.hidden = false;
  }

  function formatarTempo(segundos) {
    const m = Math.floor(segundos / 60);
    const s = String(segundos % 60).padStart(2, "0");
    return m > 0 ? `${m}:${s} min` : `${segundos}s`;
  }

  function textoTempo(arvore) {
    return arvore.segundos_para_proximo === null
      ? "Árvore carregada de frutos!"
      : `Próximo fruto em ${formatarTempo(arvore.segundos_para_proximo)}`;
  }

  function renderizarColecao(nova) {
    colecao = nova;
    moedas.textContent = colecao.moedas;
    totalColheitas.textContent = colecao.colheitas;
    vazia.hidden = colecao.arvores.length > 0;

    const prontas = colecao.arvores.filter((a) => a.frutos > 0).length;
    selo.textContent = prontas;
    selo.hidden = prontas === 0;

    grade.replaceChildren(...colecao.arvores.map((arvore) => {
      const cartao = modelo.content.firstElementChild.cloneNode(true);
      cartao.dataset.id = arvore.id;
      cartao.querySelector(".cartao-img").src = arvore.imagem;
      cartao.querySelector(".cartao-img").alt = arvore.nome;
      cartao.querySelector(".cartao-nome").textContent = arvore.nome;
      cartao.querySelector(".cartao-frutos").textContent = `🫐 Frutos: ${arvore.frutos} / ${arvore.frutos_maximos}`;
      cartao.querySelector(".cartao-tempo").textContent = textoTempo(arvore);
      cartao.querySelector(".cartao-colheitas").textContent = `Colhida ${arvore.colheitas} vez(es)`;

      // A opção de colher só aparece quando há frutos disponíveis.
      const botao = cartao.querySelector(".botao-colher");
      botao.hidden = arvore.frutos <= 0;
      botao.addEventListener("click", () => colher(arvore.id, botao));
      return cartao;
    }));
  }

  async function carregarColecao() {
    if (recarregando) return;
    recarregando = true;
    try {
      const resp = await fetch("/api/colecao");
      if (resp.ok) renderizarColecao(await resp.json());
    } catch (err) {
      console.error(err);
    } finally {
      recarregando = false;
    }
  }

  async function colher(id, botao) {
    botao.disabled = true; // evita clique duplo na mesma colheita
    try {
      const { ok, dados } = await postJSON(`/api/colecao/${id}/colher`);
      renderizarColecao(dados.colecao);
      if (!ok) {
        avisar(dados.erro, true);
        return;
      }
      aviso.hidden = true;
      document.getElementById("colheita-recompensa").textContent =
        `Você colheu ${dados.frutos_colhidos} fruto(s) e ganhou ${dados.moedas_ganhas} 🪙`;
      document.getElementById("colheita-curiosidade").textContent = dados.curiosidade;
      modalColheita.hidden = false;
    } catch (err) {
      console.error(err);
      botao.disabled = false;
    }
  }

  // Contagem regressiva local; ao nascer um fruto, busca o estado no servidor.
  setInterval(() => {
    let nasceuFruto = false;
    colecao.arvores.forEach((arvore) => {
      if (arvore.segundos_para_proximo === null) return;
      arvore.segundos_para_proximo = Math.max(0, arvore.segundos_para_proximo - 1);
      if (arvore.segundos_para_proximo === 0) nasceuFruto = true;
      const cartao = grade.querySelector(`[data-id="${arvore.id}"] .cartao-tempo`);
      if (cartao) cartao.textContent = textoTempo(arvore);
    });
    if (nasceuFruto) carregarColecao();
  }, 1000);

  renderizarColecao(colecao);

  // ---------- Enciclopédia ----------
  const botaoLivro = document.getElementById("abrir-livro");
  const modalLivro = document.getElementById("modal-livro");
  ligarModal(modalLivro);
  let planta = null;

  function preencherLista(id, itens, montar) {
    document.getElementById(id).replaceChildren(...itens.map((item, i) => {
      const li = document.createElement("li");
      montar(li, item, i);
      return li;
    }));
  }

  botaoLivro.addEventListener("click", async () => {
    try {
      if (!planta) {
        const resp = await fetch(`/api/enciclopedia/${encodeURIComponent(botaoLivro.dataset.planta)}`);
        if (!resp.ok) throw new Error("Falha ao carregar a enciclopédia");
        planta = await resp.json();
        document.getElementById("livro-nome").textContent = planta.nome;
        document.getElementById("livro-cientifico").textContent = planta.nome_cientifico;
        document.getElementById("livro-descricao").textContent = planta.descricao;
        document.getElementById("livro-curiosidade").textContent = planta.curiosidade_cultural;
        preencherLista("livro-como-plantar", planta.como_plantar, (li, passo) => {
          li.textContent = passo;
        });
      }
      // As etapas são redesenhadas a cada abertura para destacar o estágio atual.
      preencherLista("livro-estagios", planta.estagios, (li, etapa, i) => {
        li.textContent = `${etapa.nome}: ${etapa.descricao}`;
        li.classList.toggle("atual", i === estado.estagio_indice);
      });
      modalLivro.hidden = false;
    } catch (err) {
      console.error(err);
    }
  });
})();
