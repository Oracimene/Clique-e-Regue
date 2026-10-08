(() => {
  const CHAVE = "clique-e-regue:opcoes";
  const padrao = { som: true, volume: 70 };

  function ler() {
    try {
      return { ...padrao, ...JSON.parse(localStorage.getItem(CHAVE) || "{}") };
    } catch {
      return { ...padrao };
    }
  }

  function salvar(opcoes) {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(opcoes));
    } catch {
      /* navegador sem localStorage: ignora */
    }
  }

  const som = document.getElementById("opt-som");
  const volume = document.getElementById("opt-volume");
  const valorVolume = document.getElementById("valor-volume");
  const opcoes = ler();

  som.checked = opcoes.som;
  volume.value = opcoes.volume;
  valorVolume.textContent = `${opcoes.volume}%`;

  som.addEventListener("change", () => {
    opcoes.som = som.checked;
    salvar(opcoes);
  });
  volume.addEventListener("input", () => {
    opcoes.volume = Number(volume.value);
    valorVolume.textContent = `${opcoes.volume}%`;
    salvar(opcoes);
  });
})();
