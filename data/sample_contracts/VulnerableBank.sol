// SPDX-License-Identifier: MIT
// VULNERABLE CONTRACT - For testing purposes only
// Contains multiple known vulnerabilities

pragma solidity ^0.7.0;

contract VulnerableBank {
    mapping(address => uint256) public balances;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // Deposit Ether
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    // VULNERABILITY: Reentrancy (SWC-107)
    // External call before state update
    function withdraw(uint256 _amount) public {
        require(balances[msg.sender] >= _amount, "Insufficient balance");

        // BAD: External call before state change
        (bool success, ) = msg.sender.call{value: _amount}("");
        require(success, "Transfer failed");

        // State change after external call - REENTRANCY RISK
        balances[msg.sender] -= _amount;
    }

    // VULNERABILITY: tx.origin authentication (SWC-115)
    function transferOwnership(address newOwner) public {
        require(tx.origin == owner, "Not owner");
        owner = newOwner;
    }

    // VULNERABILITY: Unprotected Ether Withdrawal (SWC-105)
    // No access control on withdrawal
    function withdrawAll() public {
        uint256 balance = address(this).balance;
        payable(msg.sender).transfer(balance);
    }

    // VULNERABILITY: Unprotected selfdestruct (SWC-106)
    function destroy() public {
        selfdestruct(payable(msg.sender));
    }

    // VULNERABILITY: Unchecked return value (SWC-104)
    function unsafeSend(address payable _to, uint256 _amount) public {
        _to.send(_amount);  // Return value not checked
    }

    // VULNERABILITY: Integer Overflow (SWC-101) - Solidity < 0.8.0
    function addBalance(address _user, uint256 _amount) public {
        balances[_user] += _amount;  // Can overflow in Solidity < 0.8
    }

    // VULNERABILITY: Weak randomness (SWC-120)
    function lottery() public view returns (uint256) {
        // BAD: Using block variables for randomness
        uint256 winner = uint256(keccak256(abi.encodePacked(block.timestamp, block.difficulty, msg.sender))) % 100;
        return winner;
    }

    // Get contract balance
    function getBalance() public view returns (uint256) {
        return address(this).balance;
    }
}
