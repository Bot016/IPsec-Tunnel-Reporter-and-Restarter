# IPsec Tunnel Monitor & Recovery (for OPNsense)

Este script monitora túneis IPsec configurados no OPNsense via API e, caso algum túnel esteja inativo (sem resposta de ping), ele tenta reiniciá-lo automaticamente via SSH, utilizando o comando `swanctl --terminate`.

## 🚀 Funcionalidades

* Consulta os túneis IPsec (child SAs) configurados no OPNsense via API.
* Realiza ping simultâneo para os IPs remotos de cada túnel.
* Gera relatório JSON com o status de cada túnel (`ON` ou `OFF`).
* Reinicia túneis inativos utilizando SSH e comando `swanctl`.
* Utiliza autenticação por chave SSH.

## ⚙️ Configuração

Crie um arquivo `config.json` com os seguintes dados:

```json
{
    "api_key": "API_KEY",
    "api_secret": "API_SECRET",
    "connection_uuid": "UUID_DA_CONEXAO_PHASE1",
    "cert_path": "OPNsense.pem",
    "firewall_ip": "IP_OU_HOSTNAME_OPNSENSE",
    "web_port": PORTA_WEB (se for padrão 443),
    "ssh_port": "PORTA_SSH",
    "ssh_user": "root(ou outro, onde esta configurado a chave)",
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
Contoso - 10.1.1.1
```

O script extrai automaticamente o nome e o IP a partir desta descrição.

* O script realiza chamadas HTTPS autenticadas. Para evitar o uso de `verify=False`, é **recomendado adicionar a CA ou certificado do OPNsense localmente** e usá-la no campo `"cert_path"`.
* **Se for usar IP ao invés de hostname na URL da API**, será necessário:

  * Criar um **novo certificado** em *System > Trust > Authorities* ou *Certificates*.
  * Adicionar o **IP do firewall** ao campo **"Alternative Name"** (Subject Alternative Name - SAN) como tipo **IP Address**.
  * Atribuir esse certificado à interface Web do OPNsense em *System > Settings > Administration*.
* Isso garante que a verificação HTTPS funcione corretamente usando o IP, evitando erros de certificado inválido.

## ▶️ Como usar

Execute o script com:

```bash
python IPsec_Tunnel_Report.py
```

### O que o script faz:

1. Consulta os túneis IPsec configurados.
2. Pinga os IPs remotos.
3. Gera um arquivo (definido no config.json) com o status de cada túnel.
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

## 📃 Licença

Este projeto é open-source e está licenciado sob a licença MIT.
