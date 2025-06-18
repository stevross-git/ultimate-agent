#!/usr/bin/env python3
"""
ultimate_agent/blockchain/wallet/security.py
Blockchain and wallet management with enhanced features
"""

import time
import hashlib
import platform
import uuid
import random
from typing import Dict, Any, List
from ..contracts import SmartContractManager
from ..networks import NetworkManager as BlockchainNetworkManager


class BlockchainManager:
    """Manages blockchain operations and wallet security"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.web3 = None
        self.account = None
        self.earnings_wallet = None
        self.transaction_pool = []
        
        # Enhanced features
        self.smart_contract_manager = SmartContractManager(self)
        self.network_manager = BlockchainNetworkManager(self)
        self.multi_currency_support = self.config.getboolean('BLOCKCHAIN', 'multi_currency_support', fallback=True)
        
        self.init_blockchain()
    
    def init_blockchain(self):
        """Initialize blockchain connection and wallet"""
        try:
            # Generate wallet address for demo
            account_seed = f"{platform.node()}-{uuid.getnode()}"
            account_hash = hashlib.sha256(account_seed.encode()).hexdigest()
            self.earnings_wallet = f"0x{account_hash[:40]}"
            
            # Initialize network connections
            self.network_manager.connect_to_networks()
            
            # Initialize smart contracts
            self.smart_contract_manager.initialize_contracts()
            
            print(f"💰 Blockchain wallet initialized: {self.earnings_wallet}")
            print(f"🔗 Smart contracts: {len(self.smart_contract_manager.contracts)}")
            
        except Exception as e:
            print(f"⚠️ Blockchain initialization warning: {e}")
            self.earnings_wallet = "0x0000000000000000000000000000000000000000"
    
    def get_balance(self) -> Dict[str, float]:
        """Get current token balances across multiple currencies"""
        if self.multi_currency_support:
            return {
                'ETH': random.uniform(0.001, 0.1),
                'PAIN': random.uniform(10, 1000),
                'AI': random.uniform(5, 500),
                'BTC': random.uniform(0.0001, 0.01),
                'USDC': random.uniform(1, 100)
            }
        else:
            return {'ETH': random.uniform(0.001, 0.1)}
    
    def send_earnings(self, amount: float, task_id: str, currency: str = 'ETH') -> str:
        """Send earnings transaction"""
        try:
            transaction_hash = f"0x{hashlib.sha256(f'{task_id}{amount}{currency}{time.time()}'.encode()).hexdigest()}"
            
            # Create transaction record
            transaction = {
                'hash': transaction_hash,
                'amount': amount,
                'currency': currency,
                'task_id': task_id,
                'timestamp': time.time(),
                'status': 'confirmed',
                'gas_used': random.randint(21000, 50000),
                'gas_price': random.randint(10, 50),
                'block_number': random.randint(1000000, 2000000)
            }
            
            self.transaction_pool.append(transaction)
            
            # Keep only recent transactions
            if len(self.transaction_pool) > 100:
                self.transaction_pool = self.transaction_pool[-100:]
            
            print(f"💰 Earned {amount} {currency}: {transaction_hash}")
            return transaction_hash
            
        except Exception as e:
            print(f"❌ Failed to send earnings: {e}")
            return None
    
    def execute_smart_contract(self, contract_type: str, method: str, params: Dict) -> Dict:
        """Execute smart contract method"""
        return self.smart_contract_manager.execute_contract(contract_type, method, params)
    
    def get_transaction_history(self, limit: int = 10, currency: str = None) -> List[Dict]:
        """Get transaction history with optional currency filter"""
        transactions = self.transaction_pool[-limit:]
        
        if currency:
            transactions = [tx for tx in transactions if tx.get('currency') == currency]
        
        return transactions
    
    def estimate_gas(self, contract_type: str = None, method: str = None) -> int:
        """Estimate gas for transaction or contract method"""
        if contract_type and method:
            return self.smart_contract_manager.estimate_gas(contract_type, method)
        
        # Default transaction gas
        return 21000
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get blockchain network status"""
        return self.network_manager.get_network_status()
    
    def validate_address(self, address: str) -> bool:
        """Validate blockchain address format"""
        try:
            # Basic validation for Ethereum-style addresses
            if not address.startswith('0x'):
                return False
            if len(address) != 42:
                return False
            # Check if hex
            int(address[2:], 16)
            return True
        except ValueError:
            return False
    
    def create_multi_sig_wallet(self, required_signatures: int, signers: List[str]) -> Dict[str, Any]:
        """Create multi-signature wallet"""
        try:
            wallet_address = f"0x{hashlib.sha256(f'multisig-{time.time()}-{len(signers)}'.encode()).hexdigest()[:40]}"
            
            wallet_config = {
                'address': wallet_address,
                'required_signatures': required_signatures,
                'signers': signers,
                'created_at': time.time(),
                'transactions': []
            }
            
            print(f"🔐 Multi-sig wallet created: {wallet_address}")
            return {'success': True, 'wallet': wallet_config}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def sign_transaction(self, transaction_data: Dict) -> Dict[str, Any]:
        """Sign transaction with wallet"""
        try:
            # Simulate transaction signing
            signature = hashlib.sha256(f"{transaction_data}{self.earnings_wallet}{time.time()}".encode()).hexdigest()
            
            signed_transaction = {
                **transaction_data,
                'signature': f"0x{signature}",
                'signed_by': self.earnings_wallet,
                'signed_at': time.time()
            }
            
            return {'success': True, 'signed_transaction': signed_transaction}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_wallet_info(self) -> Dict[str, Any]:
        """Get comprehensive wallet information"""
        return {
            'address': self.earnings_wallet,
            'balances': self.get_balance(),
            'transaction_count': len(self.transaction_pool),
            'supported_currencies': list(self.get_balance().keys()) if self.multi_currency_support else ['ETH'],
            'smart_contracts': len(self.smart_contract_manager.contracts),
            'network_connections': len(self.network_manager.connected_networks),
            'wallet_type': 'standard'
        }
    
    def backup_wallet(self, backup_path: str) -> bool:
        """Backup wallet configuration and transaction history"""
        try:
            import json
            
            backup_data = {
                'wallet_address': self.earnings_wallet,
                'transaction_history': self.transaction_pool,
                'smart_contracts': self.smart_contract_manager.get_contract_addresses(),
                'network_config': self.network_manager.get_network_config() if hasattr(self.network_manager, 'get_network_config') else {},
                'backup_timestamp': time.time(),
                'backup_version': '3.0.0-modular'
            }
            
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            print(f"💾 Wallet backed up to {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ Wallet backup failed: {e}")
            return False
    
    def restore_wallet(self, backup_path: str) -> bool:
        """Restore wallet from backup"""
        try:
            import json
            
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            # Restore transaction history
            if 'transaction_history' in backup_data:
                self.transaction_pool = backup_data['transaction_history']
            
            print(f"✅ Wallet restored from {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ Wallet restore failed: {e}")
            return False
    
    def get_wallet_stats(self) -> Dict[str, Any]:
        """Get wallet statistics"""
        return {
            'address': self.earnings_wallet,
            'transaction_count': len(self.transaction_pool),
            'balance': self.get_balance(),
            'contracts_available': len(self.smart_contract_manager.contracts) if self.smart_contract_manager else 0,
            'network_status': self.network_manager.get_status() if hasattr(self.network_manager, 'get_status') else {}
        }
        
    def get_status(self) -> Dict[str, Any]:
        """Return current blockchain manager status"""
        return {
        'wallet': self.earnings_wallet,
        'balance': self.get_balance(),
        'connected_networks': len(self.network_manager.connected_networks) if hasattr(self.network_manager, 'connected_networks') else 0,
        'smart_contracts': len(self.smart_contract_manager.contracts) if hasattr(self.smart_contract_manager, 'contracts') else 0,
        'transaction_pool_size': len(self.transaction_pool)
    }

    
    def close(self):
        """Close blockchain manager and cleanup"""
        try:
            if hasattr(self, 'smart_contract_manager'):
                # Clean up smart contract manager if it has a close method
                if hasattr(self.smart_contract_manager, 'close'):
                    self.smart_contract_manager.close()
            
            if hasattr(self, 'network_manager'):
                # Clean up network manager if it has a close method
                if hasattr(self.network_manager, 'close'):
                    self.network_manager.close()
                    
            print("💰 Blockchain manager closed")
            
        except Exception as e:
            print(f"⚠️ Blockchain manager close warning: {e}")
    def backup_wallet(self, backup_path: str) -> bool:
        """Backup wallet configuration and transaction history"""
        try:
            import json
            
            backup_data = {
                'wallet_address': self.earnings_wallet,
                'transaction_history': self.transaction_pool,
                'smart_contracts': self.smart_contract_manager.get_contract_addresses(),
                'network_config': self.network_manager.get_network_config() if hasattr(self.network_manager, 'get_network_config') else {},
                'backup_timestamp': time.time(),
                'backup_version': '3.0.0-modular'
            }
            
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            print(f"💾 Wallet backed up to {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ Wallet backup failed: {e}")
            return False
    
    def restore_wallet(self, backup_path: str) -> bool:
        """Restore wallet from backup"""
        try:
            import json
            
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            # Restore transaction history
            if 'transaction_history' in backup_data:
                self.transaction_pool = backup_data['transaction_history']
            
            print(f"✅ Wallet restored from {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ Wallet restore failed: {e}")
            return False
    
    def get_wallet_stats(self) -> Dict[str, Any]:
        """Get wallet statistics"""
        return {
            'address': self.earnings_wallet,
            'transaction_count': len(self.transaction_pool),
            'balance': self.get_balance(),
            'contracts_available': len(self.smart_contract_manager.contracts) if self.smart_contract_manager else 0,
            'network_status': self.network_manager.get_status() if hasattr(self.network_manager, 'get_status') else {}
        }
    
    def close(self):
        """Close blockchain manager and cleanup"""
        try:
            if hasattr(self, 'smart_contract_manager'):
                # Clean up smart contract manager if it has a close method
                if hasattr(self.smart_contract_manager, 'close'):
                    self.smart_contract_manager.close()
            
            if hasattr(self, 'network_manager'):
                # Clean up network manager if it has a close method
                if hasattr(self.network_manager, 'close'):
                    self.network_manager.close()
                    
            print("💰 Blockchain manager closed")
            
        except Exception as e:
            print(f"⚠️ Blockchain manager close warning: {e}")
