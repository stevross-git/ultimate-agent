# Advanced Blockchain Module

This directory provides the full blockchain stack used by the Ultimate Pain Network agent.  It includes smart contract tools, multi‑currency wallets, and a lightweight network manager.  The goal is to allow the agent to simulate blockchain behaviour without heavy third‑party dependencies.

## Components

- `incentives.py` – Token economy utilities. Provides `TokenFiatExchange` for converting tokens to fiat and `EconomyManager` for tracking balances, rewards, and staking.
- `contracts/` – Smart contract framework. The `SmartContractManager` deploys and interacts with task, staking, governance, and marketplace contracts.
- `networks/` – Blockchain network connections. `NetworkManager` simulates connecting to Ethereum‑compatible networks and provides status details.
- `wallet/` – Wallet security and management. The `BlockchainManager` handles wallet creation, multi‑currency balances, transaction history, and contract execution.
- `__init__.py` – Exposes the main classes for easy import: `BlockchainManager`, `SmartContractManager`, `EconomyManager`, and `TokenFiatExchange`.

## Quick Start

```python
from ultimate_agent.blockchain import BlockchainManager
from ultimate_agent.config.settings import ConfigManager

config = ConfigManager("ultimate_agent_config.ini")
blockchain = BlockchainManager(config)

balance = blockchain.get_balance()
print("Current balance:", balance)
```

### Smart Contract Execution

The blockchain manager also exposes a `SmartContractManager` for executing on‑chain logic:

```python
contract_result = blockchain.execute_smart_contract(
    "task_rewards",
    "claimReward",
    {"task_id": "task123", "amount": 1.5}
)
print(contract_result)
```

### Deploying Custom Contracts

Custom contracts can be deployed entirely in memory:

```python
custom_config = {
    "type": "custom_rewards",
    "methods": ["distribute", "claim"],
    "description": "Custom reward distribution contract"
}
deployment = blockchain.smart_contract_manager.deploy_custom_contract(
    "MyRewards", custom_config
)
print(deployment)
```

## Status and Statistics

Each component provides status helpers for monitoring:

- `BlockchainManager.get_status()` – wallet address, balances, and connection info.
- `SmartContractManager.get_contract_statistics()` – execution counts and gas usage.
- `EconomyManager.get_balance(participant_id)` – token balance for a participant.

These utilities enable the agent to manage incentives and blockchain tasks without relying on external dependencies.

## Advanced Features

- **Multi‑sig wallet support** – create multi‑signature wallets for shared funds.
- **Gas estimation** – `BlockchainManager.estimate_gas` predicts gas usage for contract calls.
- **Token staking** – `EconomyManager.stake_tokens` lets participants earn interest.
- **Network monitoring** – `NetworkManager.get_network_status` reports connections and block height.

These extras allow the system to mimic a production blockchain environment while staying self‑contained for testing and demonstrations.
