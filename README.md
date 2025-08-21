# News Daily com Envio por E-mail

Este script:
1) Coleta notícias das fontes: Convergência Digital, TechTudo, Olhar Digital e Exame/Tech.  
2) Filtra por temas (Segurança da Informação, Cloud, Hackers, Infraestrutura).  
3) Gera um HTML com nome `dailysummaryTI_AAAA-MM-DD_HHMM.html`.  
4) Envia o HTML por e-mail (inline) via SMTP.

## Como usar
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edite .env com seu SMTP
python news_daily_email.py
```

## Agendar às 08:00 (Linux cron)
```bash
crontab -e
# Ajuste o caminho do Python e do script. Exemplo:
0 8 * * * /usr/bin/python3 /caminho/para/news_daily_email.py >> /caminho/para/news_daily_email.log 2>&1
```

## Observações
- Se algum site alterar o layout, ajuste os seletores em `get_title_and_body`.
- As palavras-chave podem ser adaptadas no dicionário `KEYWORDS`.
