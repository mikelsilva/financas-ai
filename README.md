# financas-ai

Consolidador financeiro pessoal **100% local** para **C6**, **Nubank** e **Rico** — inspirado no [Pierre](https://pierre.finance), mas sem depender de Open Finance nem de nenhuma API paga.

Em vez de integrar como instituição regulada, o projeto lê os **arquivos que os próprios bancos já exportam de graça** (CSV, OFX, Excel), normaliza tudo num schema único e responde perguntas sobre seus gastos.

## Como funciona

```
  extratos dos bancos            conectores            tabela única          análises
 ┌──────────────────┐        ┌───────────────┐      ┌─────────────┐      ┌──────────────┐
 │ Nubank  (.csv)   │───────▶│ nubank.ler()  │      │             │      │ por categoria│
 │ C6      (.ofx)   │───────▶│ c6.ler()      │─────▶│  schema +   │─────▶│ evolução mês │
 │ Rico    (.xlsx)  │───────▶│ rico.ler()    │      │ categorizar │      │ recorrências │
 └──────────────────┘        └───────────────┘      └─────────────┘      └──────────────┘
```

1. **Conectores** — cada banco tem um módulo que entende o formato nativo dele e devolve a mesma tabela padrão (`data, descricao, valor, banco, conta, categoria, id_origem`).
2. **Consolidação** — junta os bancos, remove duplicatas e ordena por data.
3. **Categorizador por regras** — classifica cada transação (Delivery, Mercado, Transporte…) via regex. Determinístico, sem IA, fácil de explicar.
4. **Análises** — gastos por categoria, fluxo mensal, maiores gastos e detecção de assinaturas recorrentes.

## Rodando a demonstração

```bash
pip install -r requirements.txt
python demo.py          # gera dados de exemplo e roda tudo
python -m pytest -q     # testes
```

A demo usa **dados sintéticos** (gerados em `dados/gerar_exemplos.py`) — nenhum dado real é commitado.

## Usando com seus dados reais

Exporte os extratos e aponte o pipeline para eles:

```python
from financas_ai import pipeline
from financas_ai.core import analise

df = pipeline.consolidar({
    "nubank": "dados/meu_nubank.csv",   # app Nubank → Conta → Exportar
    "c6":     "dados/meu_c6.ofx",       # app C6 → Extrato → Exportar OFX
    "rico":   "dados/minha_rico.xlsx",  # site Rico → Movimentação → Excel
})

print(analise.gastos_por_categoria(df, mes="2026-10"))
```

> Os extratos contêm dados financeiros pessoais. O `.gitignore` já ignora `dados/` (exceto os exemplos) — **não commite seus arquivos reais.**

## Estrutura

```
src/financas_ai/
  conectores/   nubank.py · c6.py · rico.py · ofx.py       (arquivos)
                nubank_online.py                            (Nubank API ao vivo)
                openfinance/                                (Open Finance Brasil)
  core/         schema.py · categorizador.py · analise.py
  pipeline.py   orquestra tudo
sandbox_mock/   servidor que imita o Open Finance p/ rodar offline
dados/          gerador de exemplos + seus extratos (ignorados)
tests/          pytest
demo.py         demonstração ponta a ponta
```

## Conector Pluggy — Open Finance real e gratuito (recomendado)

O caminho mais robusto para dados ao vivo. A [Pluggy](https://www.pluggy.ai) é um agregador **regulado** de Open Finance; no plano **Meu Pluggy** você conecta suas próprias contas de graça (até 5, atualização a cada 24h) e consome a API oficial — **sem engenharia reversa, sem 403**.

**Setup (uma vez):**
1. Conecte suas contas em [meu.pluggy.ai](https://meu.pluggy.ai)
2. No [dashboard.pluggy.ai](https://dashboard.pluggy.ai): crie uma aplicação, ative o conector **MeuPluggy**, copie **Client ID**, **Client Secret** e o **Item ID**
3. Defina as variáveis de ambiente e rode:

```bash
# PowerShell
$env:PLUGGY_CLIENT_ID="..."; $env:PLUGGY_CLIENT_SECRET="..."; $env:PLUGGY_ITEM_ID="..."
python rodar_pluggy.py
```

```python
from financas_ai.conectores import pluggy
df = pluggy.ler(item_ids="seu-item-id")   # lê credenciais do ambiente
```

> As credenciais ficam na sua máquina (variáveis de ambiente). O `.gitignore` já bloqueia `.env`.

## Conector Nubank ao vivo (API não-oficial)

Para quem usa Nubank, há um conector que puxa os dados direto da conta — sem exportar arquivo. Usa a biblioteca `pynubank` (engenharia reversa da API do app): faz o *discovery* dos endpoints, gera um certificado `.p12` no primeiro login (via QR code no app) e lê o feed da conta e a fatura do cartão por GraphQL.

```bash
pip install -r requirements-nubank.txt     # dependência opcional
```

```python
from financas_ai.conectores import nubank_online
df = nubank_online.ler(cpf="000...", senha="...")   # 1º uso: escaneia o QR
```

> ⚠️ **Segurança:** este conector usa suas credenciais do Nubank. Rode **só na sua máquina**. O certificado `.p12` fica no seu computador e o `.gitignore` já impede que ele (e os `.env`) subam pro Git.

## Conector Open Finance Brasil (sandbox)

Além dos arquivos, o projeto tem um conector que fala o **protocolo oficial do Open Finance Brasil** — o mesmo que os bancos usam. Ele implementa o fluxo completo:

```
token (OAuth2/FAPI)  →  criar consentimento  →  autorizar  →  ler contas + cartões  →  schema
```

Para rodar **offline, sem certificado**, há um **servidor mock** que responde no mesmo formato da spec (accounts, credit-cards-accounts, consents, transações paginadas) com dados sintéticos:

```bash
# terminal 1 — sobe o mock
python sandbox_mock/servidor.py

# terminal 2 — roda o conector contra o mock
python -c "from financas_ai.conectores.openfinance import ler; print(ler().head())"
```

### Apontando para o sandbox oficial

Quando você gerar seus certificados no diretório de sandbox do Open Finance, é só definir as variáveis de ambiente — **nenhuma linha de código muda**:

```bash
export OFB_BASE_AUTH="https://auth.seu-sandbox.openfinancebrasil.org.br"
export OFB_BASE_RECURSOS="https://api.seu-sandbox.openfinancebrasil.org.br"
export OFB_CLIENT_ID="seu-client-id"
export OFB_CERT="/caminho/transport.pem"   # mTLS
export OFB_CHAVE="/caminho/signing.key"    # private_key_jwt (PS256)
```

```python
from financas_ai.conectores.openfinance import ler, OpenFinanceConfig
df = ler(OpenFinanceConfig.sandbox_do_ambiente())
```

O conector detecta sozinho: **sem chave → modo mock; com chave → assina o JWT e usa mTLS** de verdade.

> O que está pronto é o **contrato e o fluxo** (OAuth2/FAPI, consentimento, mapeamento das APIs). O acesso ao sandbox oficial depende do seu cadastro e certificados no diretório do Open Finance — que são de graça, mas exigem esse setup.

## Bot financeiro (cérebro do assistente)

O módulo `financas_ai.bot` é o "cérebro" que um canal (WhatsApp/Telegram) usa. Funciona por linha de comando:

```bash
python bot.py sync                      # puxa da Pluggy e mostra as compras NOVAS
python bot.py perguntar "quanto gastei com delivery?"
python bot.py relatorio                 # resumo pronto pra enviar
```

- **`sync`** compara com `dados/estado_bot.json` e devolve só o que chegou desde a última vez — base do "me avisa quando comprar".
- **`perguntar`** responde via **Ollama** local (grátis, offline). Sem Ollama, cai num modo simples por regras.

Para as respostas com IA, instale o [Ollama](https://ollama.com) e baixe um modelo:

```bash
ollama pull llama3.2       # ou outro modelo; defina OLLAMA_MODEL para trocar
```

## Próximos passos (roadmap)

- [ ] Camada conversacional local com **Ollama** (pergunta em português → filtro no pandas), mantendo o custo zero
- [ ] Dashboard (Streamlit) com os gráficos
- [ ] Bot (Telegram) rodando num celular antigo via Termux
- [ ] Mais regras de categorização a partir dos seus próprios extratos

## Por que isso é relevante num portfólio de dados

Mostra o ciclo completo de engenharia de dados: **ingestão de formatos heterogêneos → normalização em schema comum → deduplicação → enriquecimento (categorização) → análise**, com testes e um conector por fonte — o padrão que se usa em qualquer pipeline de dados real.

---
Licença MIT.
