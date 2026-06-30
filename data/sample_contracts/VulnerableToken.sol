// SPDX-License-Identifier: MIT
// Token contract with access control issues
pragma solidity ^0.7.6;

contract VulnerableToken {
    string public name = "VulnToken";
    string public symbol = "VTK";
    uint8 public decimals = 18;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    address public owner;
    bool public paused;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(uint256 _initialSupply) {
        owner = msg.sender;
        totalSupply = _initialSupply * 10 ** uint256(decimals);
        balanceOf[msg.sender] = totalSupply;
    }

    // VULNERABILITY: No access control - anyone can mint
    function mint(address _to, uint256 _amount) public {
        totalSupply += _amount;
        balanceOf[_to] += _amount;
        emit Transfer(address(0), _to, _amount);
    }

    // VULNERABILITY: No access control - anyone can burn others' tokens
    function burn(address _from, uint256 _amount) public {
        balanceOf[_from] -= _amount;
        totalSupply -= _amount;
        emit Transfer(_from, address(0), _amount);
    }

    // VULNERABILITY: Integer overflow possible (Solidity < 0.8)
    function transfer(address _to, uint256 _value) public returns (bool) {
        require(balanceOf[msg.sender] >= _value, "Insufficient balance");
        balanceOf[msg.sender] -= _value;
        balanceOf[_to] += _value;  // Potential overflow
        emit Transfer(msg.sender, _to, _value);
        return true;
    }

    function approve(address _spender, uint256 _value) public returns (bool) {
        allowance[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value);
        return true;
    }

    function transferFrom(address _from, address _to, uint256 _value) public returns (bool) {
        require(balanceOf[_from] >= _value, "Insufficient balance");
        require(allowance[_from][msg.sender] >= _value, "Allowance exceeded");
        balanceOf[_from] -= _value;
        balanceOf[_to] += _value;
        allowance[_from][msg.sender] -= _value;
        emit Transfer(_from, _to, _value);
        return true;
    }

    // VULNERABILITY: tx.origin for pause
    function pause() public {
        require(tx.origin == owner, "Not owner");
        paused = true;
    }

    // VULNERABILITY: Delegatecall to user address
    function delegateAction(address _target, bytes memory _data) public {
        (bool success, ) = _target.delegatecall(_data);
        require(success, "Delegatecall failed");
    }
}
