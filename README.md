# YouTube Resumidor

> Resumidor automático de vídeos do YouTube com saída em **Português do Brasil**, usando Google Gemini AI.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.1.3-lightgrey)
![Gemini](https://img.shields.io/badge/Google%20Gemini-2.5%20Flash-orange)
![Vercel](https://img.shields.io/badge/Deploy-Vercel-black)

---

## Sobre o Projeto

O **YouTube Resumidor** recebe a URL de um vídeo do YouTube, busca automaticamente sua transcrição e usa a IA do Google Gemini para gerar um resumo detalhado e estruturado em Português do Brasil — mesmo que o vídeo original seja em inglês.

O projeto oferece duas interfaces:

- **Interface Web** — acesse pelo navegador, cole a URL e leia o resumo na tela
- **Widget iOS** — integração com o app [Scriptable](https://scriptable.app/) para gerar resumos diretamente da tela inicial do iPhone ou via Share Sheet

---

## Tech Stack

| Camada | Tecnologia |
|---|---|
| Backend | Flask 3.1.3 |
| Rate Limiting | flask-limiter 4.1.1 |
| Transcrição | youtube-transcript-api 1.2.4 |
| IA | Google Gemini 2.5 Flash (google-generativeai 0.8.6) |
| Frontend | HTML5 + JavaScript puro |
| Renderização Markdown | marked.js (CDN) |
| Proteção XSS | DOMPurify (CDN) |
| Widget iOS | Scriptable (WebView + ListWidget) |
| Deploy | Vercel (runtime Python) |
| Túnel local | Ngrok |

---

## Pré-requisitos

- Python 3.9 ou superior
- Conta no [Google AI Studio](https://aistudio.google.com/app/apikey) para obter a chave da API Gemini
- [Ngrok](https://ngrok.com/) — apenas se quiser usar o widget iOS com o servidor local
- App [Scriptable](https://apps.apple.com/br/app/scriptable/id1405459188) no iPhone — apenas para o widget

---

## Instalação e Execução Local

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd yt_resumo_video_link

# 2. Crie e ative o ambiente virtual
python3 -m venv venv
source venv/bin/activate       # macOS / Linux
# ou: venv\Scripts\activate    # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure a chave da API
export GEMINI_API_KEY="sua_chave_gemini_aqui"

# 5. Inicie o servidor
python server.py
```

O servidor sobe em `http://localhost:5001`. Acesse pelo navegador, cole uma URL do YouTube e clique em **Resumir**.

---

## Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `GEMINI_API_KEY` | Sim | Chave da API do Google Gemini. Obtenha em [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `FLASK_DEBUG` | Não | Defina como `"true"` para ativar o modo debug (nunca use em produção) |

---

## Widget iOS (Scriptable)

O widget permite gerar resumos direto da tela inicial do iPhone ou compartilhando um vídeo via Share Sheet.

### Configuração

1. Instale o app **Scriptable** na App Store
2. Abra o app, crie um novo script e cole o conteúdo de `YoutubeWidget.js`
3. Atualize o valor de `SERVER_URL` na **linha 8** com a URL do seu servidor:
   - Em produção: URL do Vercel (ex: `https://seu-projeto.vercel.app/summarize`)
   - Em desenvolvimento local: URL do Ngrok (veja abaixo)
4. Salve o script e adicione à tela inicial como widget

### Expor o servidor local com Ngrok

```bash
# Em um terminal separado (com o servidor já rodando):
ngrok http 5001

# Copie a URL exibida (ex: https://abc123.ngrok-free.app)
# Cole em SERVER_URL no arquivo YoutubeWidget.js (linha 8)
# Lembre de adicionar /summarize ao final da URL
```

---

## Como Funciona

```
Usuário informa a URL do YouTube
          ↓
Servidor extrai o ID do vídeo (ex: dQw4w9WgXcQ)
          ↓
youtube-transcript-api busca a transcrição
  Prioridade: pt-BR → en → qualquer idioma disponível
          ↓
Transcrição enviada ao Google Gemini 2.5 Flash
  Prompt instrui: gerar resumo em Português do Brasil
          ↓
Resposta retornada como JSON { "summary": "..." }
          ↓
Frontend renderiza o Markdown e sanitiza o HTML
```

---

## API

### `POST /summarize`

Gera o resumo de um vídeo do YouTube.

**Requisição:**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Resposta (sucesso — HTTP 200):**
```json
{
  "summary": "## Título do Vídeo\n\nResumo estruturado em Português..."
}
```

**Resposta (erro):**
```json
{
  "error": "Descrição do erro"
}
```

| Código | Situação |
|---|---|
| 400 | URL ausente, inválida ou corpo da requisição incorreto |
| 404 | Transcrição não disponível para o vídeo |
| 429 | Limite de requisições excedido (máx. 10/minuto por IP) |

---

## Deploy no Vercel

O arquivo `vercel.json` já está configurado. Basta executar:

```bash
vercel
```

Após o deploy, atualize `SERVER_URL` no `YoutubeWidget.js` com a URL gerada pelo Vercel.

---

## Estrutura de Arquivos

```
yt_resumo_video_link/
├── server.py            # Backend Flask: rotas, transcrição e sumarização
├── requirements.txt     # Dependências Python com versões fixas
├── vercel.json          # Configuração de deploy para o Vercel
├── YoutubeWidget.js     # Widget iOS para o app Scriptable
├── test_api.py          # Script de teste para a lógica de transcrição
└── templates/
    └── index.html       # Interface web (HTML + JS inline)
```

---

## Solução de Problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `WARNING: GEMINI_API_KEY not found` | Variável de ambiente não definida | Execute `export GEMINI_API_KEY="sua_chave"` |
| Widget exibe "Falha na conexão" | Ngrok não está rodando ou URL desatualizada | Reinicie o Ngrok e atualize `SERVER_URL` no script |
| Erro "Could not retrieve transcript" | Vídeo sem legendas ou legendas restritas | Tente outro vídeo que tenha legendas disponíveis |
| HTTP 429 no endpoint `/summarize` | Limite de 10 requisições/minuto atingido | Aguarde um minuto antes de tentar novamente |
