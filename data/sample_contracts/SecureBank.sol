// SPDX-License-Identifier: MIT
// SECURE CONTRACT - Demonstrates best practices
pragma solidity 0.8.20;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract SecureBank is ReentrancyGuard, Ownable {
    mapping(address => uint256) private balances;

    event Deposit(address indexed user, uint256 amount);
    event Withdrawal(address indexed user, uint256 amount);

    constructor() Ownable() {}

    function deposit() external payable {
        require(msg.value > 0, "Must deposit > 0");
        balances[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    // SECURE: Uses checks-effects-interactions + ReentrancyGuard
    function withdraw(uint256 _amount) external nonReentrant {
        require(balances[msg.sender] >= _amount, "Insufficient balance");

        // Effects before interactions
        balances[msg.sender] -= _amount;

        // Interaction last
        (bool success, ) = payable(msg.sender).call{value: _amount}("");
        require(success, "Transfer failed");

        emit Withdrawal(msg.sender, _amount);
    }

    // SECURE: Uses msg.sender, not tx.origin
    function transferOwnership(address newOwner) public override onlyOwner {
        require(newOwner != address(0), "Invalid address");
        super.transferOwnership(newOwner);
    }

    // SECURE: Access controlled
    function emergencyWithdraw() external onlyOwner {
        uint256 balance = address(this).balance;
        (bool success, ) = payable(owner()).call{value: balance}("");
        require(success, "Transfer failed");
    }

    function getBalance(address _user) external view returns (uint256) {
        return balances[_user];
    }

    function getContractBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
