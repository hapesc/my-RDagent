# ADR 004: Python Protocol for Plugin System

## Status
Accepted

## Context
The Agentic R&D Platform needs to be extensible, allowing developers to add new scenarios, planners, and tools without modifying the core engine. We need a way to define contracts that plugins must follow.

We considered the following options:
1.  **Abstract Base Classes (ABC)**: Traditional inheritance-based approach, but requires explicit inheritance and can lead to complex metaclass hierarchies.
2.  **Class Registration/Decorators**: Flexible, but doesn't provide strong static typing or IDE support.
3.  **Python Protocols (typing.Protocol)**: Structural subtyping (duck typing) that defines the interface expected by the consumer.

## Decision
We chose **Python Protocol** to define the interface contracts for the plugin system.

The core plugin contracts are defined in `plugins/contracts.py`. We use a `PluginBundle` that groups multiple Protocol interfaces, such as `ScenarioLoader`, `RDLPlanner`, and `AgentRunner`. The platform's components interact with these protocols instead of concrete classes.

## Consequences
- **Duck Typing Support**: Any class that implements the required methods and attributes is automatically a valid plugin, without needing to inherit from a specific base class.
- **Improved Type Checking**: Static analysis tools (like mypy) and IDEs can provide better autocompletion and error checking based on the protocol definitions.
- **Runtime Verification**: By using the `@runtime_checkable` decorator, the platform can perform `isinstance()` checks at runtime to verify that a plugin correctly implements the interface.
- **No Metaclass Complexity**: Avoids potential conflicts when a plugin class needs to inherit from other libraries' classes that also use custom metaclasses.
- **Loose Coupling**: The core engine and the plugins are decoupled, as they only share the interface definitions.
