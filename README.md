# IPsec Tunnel Monitor & Recovery (for OPNsense)

Este script monitora túneis IPsec configurados no OPNsense via API e, caso algum túnel esteja inativo (sem resposta de ping), ele tenta reiniciá-lo automaticamente via SSH, utilizando o comando `swanctl --terminate`.

## 🚀 Funcionalidades

* Consulta os túneis IPsec (child SAs) configurados no OPNsense via API.
* Realiza ping simultâneo para os IPs remotos de cada túnel.
* Gera relatório JSON com o status de cada túnel (`ON` ou `OFF`).
* Reinicia túneis inativos utilizando SSH e comando `swanctl`.
* Utiliza autenticação por chave SSH.

## 🧱 Requisitos

* Python 3.7+
* Acesso à API do OPNsense
* Acesso SSH ao OPNsense com chave privada
* Bibliotecas:

  * `requests`
  * `paramiko`
  * `concurrent.futures`

Instale via:

```bash
pip install requests paramiko
```

## ⚙️ Configuração

Crie um arquivo `config.json` com os seguintes dados:

```json
{
    "api_key": "SUA_API_KEY",
    "api_secret": "SUA_API_SECRET",
    "connection_uuid": "UUID_DA_CONEXAO",
    "ssh_host": "SEU_OPNSENSE",
    "ssh_port": "porta_do_SSH",
    "ssh_user": "root",
    "ssh_key_path": "CAMINHO/PARA/id_ed25519",
    "output_path": "tunnle_report.json"
}
```

### 🔧 Requisitos de Configuração no OPNsense

A *descrição* da Fase 2 (child SA) deve obrigatoriamente seguir o formato:

```
Nome da Empresa - IP para pingar
```

Exemplo:

```
Microsoft - 10.1.1.1
```

O script extrai automaticamente o nome e o IP a partir desta descrição.

## ▶️ Como usar

Execute o script com:

```bash
python IPsec_Tunnel_Report.py
```

### O que o script faz:

1. Consulta os túneis IPsec configurados.
2. Pinga os IPs remotos.
3. Gera um arquivo `tunnle_report.json` com o status de cada túnel.
4. Reinicia automaticamente túneis que estiverem inativos.

## 📂 Exemplo de saída (`tunnle_report.json`)

```json
[
    {
        "tunel": 1,
        "empresa": "Exemplo LTDA",
        "status": "ON",
        "uuid": "abcd-1234..."
    },
    {
        "tunel": 2,
        "empresa": "Outra Empresa",
        "status": "OFF",
        "uuid": "efgh-5678..."
    }
]
```


