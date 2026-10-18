<div align="center">

# `google-ai-reversed`

**free gemini & google ai overview scraper. zero api keys. no rate limits.**

[![Discord](https://img.shields.io/badge/Discord-discord.gg%2Fcse-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/cse)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Engine](https://img.shields.io/badge/Engine-Chrome%20131%20JA3-00C853?style=for-the-badge&logo=googlechrome&logoColor=white)](#how-it-works)
[![License](https://img.shields.io/badge/License-MIT-111111?style=for-the-badge)](LICENSE)

<br/>

<p align="center">
  <a href="https://discord.gg/cse">
    <img src="https://lanyard.cnrad.dev/api/1420036436505268244?bg=0d1117&borderRadius=10px&showDisplayName=true&animated=true" alt="Developer Discord Status" />
  </a>
</p>
<sub><i>Hanging out at <a href="https://discord.gg/cse">discord.gg/cse</a>.</i></sub>

<br/><br/>

</div>

---

literally just threw this script together in 15 minutes of reversing google's search endpoints because i didn't feel like making a cloud console account or paying for gemini tokens.

google serves the full gemini response + all source citations right on `udm=50`. this script grabs the session tokens, mimics a real chrome 131 tls handshake, hits the async endpoint, and spits out the answer.

it's just a script. fork it, break it, push commits, make pull requests, rewrite it in rust, do whatever you want.

<br/>

```
                +---------------------------------------+
                |         search query input            |
                +-------------------+-------------------+
                                    |
                                    v
                     [ GET /search?q=...&udm=50 ]
                     (TLS Fingerprint: Chrome 131)
                                    |
            +-----------------------+-----------------------+
            |                                               |
    [ curl_cffi direct ]                           [ Playwright fallback ]
    (extract session tokens)                       (if anti-bot challenge)
            |                                               |
            +-----------------------+-----------------------+
                                    |
                        Tokens Extracted:
                 stkp • xsrf • elrc • srtst • ei
                                    |
                                    v
               [ GET /async/folif?sclient=aim-smartcompose ]
                                    |
                                    v
                 [ Regex + Comment Unpack (TgQPHd) ]
                                    |
             +----------------------+----------------------+
             |                                             |
             v                                             v
    Generative Synthesis                         Ranked Source Citations
    (Grounded response text)                     (URLs, domains, metadata)
```

---

## ⚡ Features

- **No API keys**: zero setup, no cloud console, no credit cards.
- **Full citations**: dumps the exact source urls & site names google used to generate the answer.
- **Stealth JA3**: uses `curl_cffi` to impersonate browser tls & http/2 headers so google doesn't complain.
- **Playwright fallback**: boots headless chromium automatically if google throws a challenge.
- **Save to file**: optionally writes output straight to `.txt`.

---

## 📊 Comparison

| | Official Gemini API | This Script |
| :--- | :--- | :--- |
| **Cost** | Paid / Quotas | **$0** |
| **API Key** | Required | **None** |
| **Web Sources** | Needs search grounding config | **Extracted automatically** |
| **Rate Limits** | 15 RPM free tier | **Whatever your connection handles** |
| **Setup Time** | 10 minutes in GCP | **10 seconds** |

---

## 🚀 Setup & Run

### 1. Install Dependencies

```bash
git clone https://github.com/snipe1337/google-ai-reversed.git
cd google-ai-reversed
pip install -r requirements.txt
playwright install chromium
```

### 2. Run It

```bash
python googleAiReversed.py
```

```text
[ryze] [info] enter query: explain how quantum entanglement works in simple terms
[ryze] [info] resolving session tokens for 'explain how quantum entanglement works in simple terms'...
[ryze] [success] session tokens acquired successfully
[ryze] [info] sending request for query (impersonate='chrome131')...
[ryze] [success] request successful (84,219 bytes received)

=================================================================
response:
=================================================================
Quantum entanglement is a phenomenon in quantum physics where two or 
more particles become interconnected such that the physical state of 
one instantly dictates the state of the other, no matter the distance 
separating them...

=================================================================
sources (4 found):
=================================================================
1. What Is Quantum Entanglement? [caltech.edu]
   url: https://scienceexchange.caltech.edu/topics/quantum-science-explained/entanglement
2. Einstein's 'Spooky Action at a Distance' Paradox [scientificamerican.com]
   url: https://www.scientificamerican.com/article/what-is-quantum-entanglement/
3. Quantum Entanglement Explained Simply [quantamagazine.org]
   url: https://www.quantamagazine.org/entanglement-made-simple-20160428/
```

---

## 💬 Community

if you have questions, want to talk reverse engineering, or just chill:

<p align="center">
  <a href="https://discord.gg/cse">
    <img src="https://invidget.switchblade.xyz/cse" alt="Discord Server discord.gg/cse" />
  </a>
</p>

<p align="center">
  👉 <b><a href="https://discord.gg/cse">discord.gg/cse</a></b>
</p>

---

## ⭐ Star

if this saved you from paying for api tokens or you just like cool reverse-engineering scripts, drop a star.

```bash
gh repo star snipe1337/google-ai-reversed
```

---

## ⚖️ Disclaimer

*educational & research purposes only. it's just scraping public endpoints. do what you want with it.*
