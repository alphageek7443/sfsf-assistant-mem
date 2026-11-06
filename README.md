# sfsf-assistant-mem

A LangGraph A2A agent for SAP Joule on BTP Cloud Foundry, powered by SAP GenAI Hub.

## Quick Start

### Local Development

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your AI Core service key
python -m app
# Test: curl http://localhost:8080/.well-known/agent.json
```

### Deploy to Cloud Foundry

```bash
cf login -a https://api.cf.<landscape>.hana.ondemand.com
cf push
```

### Connect to Joule

1. Create BTP destination `SfsfAssistantMem_A2A` pointing to `https://<app-name>.cfapps.<landscape>.hana.ondemand.com`
2. Deploy the Joule capability:
   ```bash
   cd joule-capability
   joule login 
   joule deploy ./da.sapdas.yaml --compile -n "sfsf_assistant_mem_a2a"
   ```

## Project Structure

```
sfsf-assistant-mem/
├── app/
│   ├── __main__.py          # Server entry point
│   ├── agent.py             # LangGraph ReAct agent
│   ├── agent_executor.py    # A2A protocol bridge
│   ├── agent_card.py        # Agent Card (discovery)
│   └── tools.py             # Your custom tools
├── joule-capability/
│   ├── capability.sapdas.yaml       # Capability definition (schema 3.28.0)
│   ├── capability_context.yaml      # Multi-turn context variables
│   ├── da.sapdas.yaml               # DA descriptor (schema 1.4.0)
│   ├── functions/
│   │   └── call_agent.yaml          # A2A agent-request function
│   └── scenarios/
│       └── invoke_agent.yaml        # User intent mapping
├── manifest.yml             # CF deployment
├── requirements.txt
├── Procfile
├── runtime.txt
└── .env.example
```

## Customization

1. Edit `app/tools.py` to add your agent's tools
2. Edit `app/agent.py` SYSTEM_INSTRUCTION for behavior
3. Edit `app/agent_card.py` skills to match your tools
4. Edit `joule-capability/capability.sapdas.yaml` scenario description
