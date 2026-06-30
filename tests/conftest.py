"""Shared fixtures for the test suite."""

import sys
import os
import pytest

# Ensure the backend package is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# ── Sample contracts ────────────────────────────────────────────

VULNERABLE_CONTRACT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

contract VulnerableBank {
    mapping(address => uint256) public balances;
    address public owner;

    constructor() { owner = msg.sender; }

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 _amount) public {
        require(balances[msg.sender] >= _amount);
        (bool success, ) = msg.sender.call{value: _amount}("");
        require(success);
        balances[msg.sender] -= _amount;
    }

    function transferOwnership(address newOwner) public {
        require(tx.origin == owner);
        owner = newOwner;
    }

    function destroy() public {
        selfdestruct(payable(msg.sender));
    }

    function unsafeSend(address payable _to, uint256 _amount) public {
        _to.send(_amount);
    }

    function lottery() public view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(block.timestamp, block.difficulty))) % 100;
    }
}
"""

SECURE_CONTRACT = """
// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

contract SecureBank {
    mapping(address => uint256) private balances;
    address public owner;
    bool private locked;

    modifier nonReentrant() {
        require(!locked, "No reentrancy");
        locked = true;
        _;
        locked = false;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() { owner = msg.sender; }

    function deposit() external payable {
        require(msg.value > 0);
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 _amount) external nonReentrant {
        require(balances[msg.sender] >= _amount);
        balances[msg.sender] -= _amount;
        (bool success, ) = payable(msg.sender).call{value: _amount}("");
        require(success);
    }
}
"""

GAS_INEFFICIENT_CONTRACT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract GasWaster {
    uint256[] public data;
    mapping(address => uint256) public balances;

    function loopStorage() public {
        for (uint i = 0; i < data.length; i++) {
            data[i] = data[i] + 1;
        }
    }

    function memoryParam(uint256[] memory ids) external {
        for (uint i = 0; i < ids.length; i++) {
            balances[msg.sender] += ids[i];
        }
    }

    function checkZero(uint256 x) public pure returns (bool) {
        return x > 0;
    }
}
"""


@pytest.fixture
def vulnerable_code():
    return VULNERABLE_CONTRACT


@pytest.fixture
def secure_code():
    return SECURE_CONTRACT


@pytest.fixture
def gas_code():
    return GAS_INEFFICIENT_CONTRACT
