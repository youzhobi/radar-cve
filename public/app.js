/*
  app.js
  -------
  Este arquivo roda dentro do NAVEGADOR de quem visita o site
  (não no seu computador, nem no Firebase). A missão dele é:

    1. Conectar no Firestore (o banco de dados na nuvem)
    2. Pedir os dados que o Python já enviou pra lá
    3. Desenhar esses dados na tela (cartões + tabela)
    4. Fazer os botões de filtro funcionarem

  Pense nisso como o "garçom" do site: ele vai até a cozinha
  (Firestore), busca o prato pronto (os dados) e serve na mesa
  (a página que a pessoa está vendo).
*/

// ------------------------------------------------------------------
// PASSO 1: Configuração do Firebase.
// Esses valores você pega no Console do Firebase, em:
//   Configurações do projeto > Seus apps > Configuração do SDK
// Eles NÃO são segredo - são só o "endereço" público do seu projeto.
// Quem protege seus dados de verdade são as REGRAS do Firestore
// (arquivo firestore.rules), não esconder esses valores.
// ------------------------------------------------------------------
const configuracaoFirebase = {
  apiKey: "AIzaSyBn0lqeWQQZc0FlmelTR_UD_hEOXtInqGc",
  authDomain: "radar-cve.firebaseapp.com",
  projectId: "radar-cve",
  storageBucket: "radar-cve.firebasestorage.app",
  messagingSenderId: "814298849616",
  appId: "1:814298849616:web:9473754558f7e7d432cc55",
};

// PASSO 2: inicia a conexão com o Firebase usando a configuração acima.
firebase.initializeApp(configuracaoFirebase);
const db = firebase.firestore();

// Guardamos aqui, na memória do navegador, a lista completa de CVEs
// assim que ela chegar - assim, trocar o filtro não precisa pedir
// os dados de novo ao Firestore toda hora.
let todasAsCves = [];
let filtroAtual = "TODAS";

/*
  PASSO 3: busca o resumo por severidade (documento único no
  Firestore) e desenha os cartõezinhos no topo da página.
*/
function carregarResumo() {
  db.collection("resumo")
    .doc("por_severidade")
    .get()
    .then((documento) => {
      if (!documento.exists) return;

      const dados = documento.data(); // ex: { HIGH: 12, MEDIUM: 8, ... }
      const container = document.getElementById("resumo-severidade");
      container.innerHTML = ""; // limpa antes de desenhar de novo

      for (const [severidade, total] of Object.entries(dados)) {
        const cartao = document.createElement("div");
        cartao.className = "cartao-severidade";
        cartao.innerHTML = `
          <div class="numero">${total}</div>
          <div class="rotulo">${severidade}</div>
        `;
        container.appendChild(cartao);
      }
    });
}

/*
  PASSO 3.1: busca a tendência por dia (documento "por_dia") e
  desenha um gráfico de barrinhas bem simples - sem biblioteca
  nenhuma, só divs com altura proporcional ao valor.
*/
function carregarTendencia() {
  db.collection("resumo")
    .doc("por_dia")
    .get()
    .then((documento) => {
      if (!documento.exists) return;

      const dados = documento.data(); // ex: { "2026-08-10": 2, "2026-08-11": 5 }
      const dias = Object.keys(dados).sort(); // ordem cronológica
      const maiorValor = Math.max(...Object.values(dados));

      const container = document.getElementById("grafico-tendencia");
      container.innerHTML = "";

      for (const dia of dias) {
        const total = dados[dia];
        // altura da barra em % do maior valor, com um mínimo pra sempre aparecer algo
        const alturaPercentual = Math.max((total / maiorValor) * 100, 8);

        const coluna = document.createElement("div");
        coluna.className = "barra-dia";
        coluna.innerHTML = `
          <div class="barra" style="height: ${alturaPercentual}%" title="${total} CVEs"></div>
          <span class="rotulo-dia">${dia.slice(5)}</span>
        `;
        container.appendChild(coluna);
      }
    });
}

/*
  PASSO 3.2: busca os produtos recorrentes (documento
  "produtos_recorrentes") e desenha a listinha.
*/
function carregarProdutosRecorrentes() {
  db.collection("resumo")
    .doc("produtos_recorrentes")
    .get()
    .then((documento) => {
      if (!documento.exists) return;

      const dados = documento.data(); // ex: { "Roteador X": 3, "Apache 2.4": 2 }
      const lista = document.getElementById("lista-produtos-recorrentes");
      lista.innerHTML = "";

      // ordena do produto com mais CVEs pro com menos
      const entradas = Object.entries(dados).sort((a, b) => b[1] - a[1]);

      if (entradas.length === 0) {
        lista.innerHTML = `<li style="color: var(--texto-fraco)">Nenhum produto recorrente ainda.</li>`;
        return;
      }

      for (const [produto, total] of entradas) {
        const item = document.createElement("li");
        item.innerHTML = `
          <span>${produto}</span>
          <span class="contagem">${total} CVEs</span>
        `;
        lista.appendChild(item);
      }
    });
}

/*
  PASSO 4: busca a lista de CVEs recentes no Firestore, já
  ordenadas da mais grave para a menos grave.
*/
function carregarCves() {
  const estado = document.getElementById("estado-carregamento");

  db.collection("cves_recentes")
    .orderBy("score", "desc")
    .get()
    .then((snapshot) => {
      todasAsCves = snapshot.docs.map((doc) => doc.data());
      estado.style.display = "none";
      desenharTabela();
    })
    .catch((erro) => {
      estado.textContent = "Erro ao carregar os dados. Veja o console (F12).";
      console.error(erro);
    });
}

/*
  PASSO 5: desenha as linhas da tabela na tela, respeitando o
  filtro de severidade que estiver selecionado no momento.
*/
function desenharTabela() {
  const corpo = document.getElementById("corpo-tabela");
  corpo.innerHTML = "";

  const listaFiltrada =
    filtroAtual === "TODAS"
      ? todasAsCves
      : todasAsCves.filter((cve) => cve.severidade === filtroAtual);

  for (const cve of listaFiltrada) {
    const linha = document.createElement("tr");
    const severidadeClasse = (cve.severidade || "").toLowerCase();

    linha.innerHTML = `
      <td class="id-cve">${cve.id}</td>
      <td><span class="pilula-severidade ${severidadeClasse}">${cve.severidade}</span></td>
      <td>${cve.score ?? "-"}</td>
      <td>${cve.descricao}</td>
      <td>${(cve.data_publicacao || "").split("T")[0]}</td>
    `;
    corpo.appendChild(linha);
  }
}

/*
  PASSO 6: liga os botões de filtro (Todas / Critical / High / ...)
  Cada clique troca o filtro atual e redesenha a tabela.
*/
function configurarFiltros() {
  const botoes = document.querySelectorAll(".filtro");

  botoes.forEach((botao) => {
    botao.addEventListener("click", () => {
      // tira "ativo" de todos os botões, e coloca só no que foi clicado
      botoes.forEach((b) => b.classList.remove("ativo"));
      botao.classList.add("ativo");

      filtroAtual = botao.dataset.filtro;
      desenharTabela();
    });
  });
}

// PASSO 7: quando a página terminar de carregar, roda tudo em ordem.
document.addEventListener("DOMContentLoaded", () => {
  configurarFiltros();
  carregarResumo();
  carregarCves();
  carregarTendencia();
  carregarProdutosRecorrentes();
});
