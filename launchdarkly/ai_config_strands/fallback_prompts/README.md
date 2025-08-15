# Fallback Prompts Directory

This directory contains fallback prompt files for the multi-agent system. These prompts are used when LaunchDarkly AI Config is unavailable or fails to load.

## Files

### `teacher_orchestrator_fallback_prompt.txt`
- **Purpose**: Fallback prompt for the teacher-orchestrator agent
- **Role**: Educational orchestrator that routes queries to specialized agents
- **Usage**: Used when AI Config fails to load for `teacher-orchestrator` role

### `general_assistant_fallback_prompt.txt`
- **Purpose**: Fallback prompt for the general assistant agent
- **Role**: General knowledge assistant for non-specialized queries
- **Usage**: Used when AI Config fails to load for `general-assistant` role

### `english_assistant_fallback_prompt.txt`
- **Purpose**: Fallback prompt for the english assistant agent
- **Role**: Advanced English education assistant for writing, grammar, and literature
- **Usage**: Used when AI Config fails to load for `english-assistant` role

### `language_assistant_fallback_prompt.txt`
- **Purpose**: Fallback prompt for the language assistant agent
- **Role**: Specialized assistant for language translation and learning
- **Usage**: Used when AI Config fails to load for `language-assistant` role

### `math_assistant_fallback_prompt.txt`
- **Purpose**: Fallback prompt for the math assistant agent
- **Role**: Specialized assistant for mathematics education and problem-solving
- **Usage**: Used when AI Config fails to load for `math-assistant` role

### `computer_science_assistant_fallback_prompt.txt`
- **Purpose**: Fallback prompt for the computer science assistant agent
- **Role**: Specialized assistant for computer science education and programming
- **Usage**: Used when AI Config fails to load for `computer-science-assistant` role

## Fallback Strategy

The multi-agent system uses a three-tier fallback strategy:

1. **Primary**: Dynamic prompt from LaunchDarkly AI Config
2. **Secondary**: Static prompt from files in this directory
3. **Tertiary**: Ultimate hardcoded fallback in the code

## Maintenance

- Keep these files in sync with the latest approved prompts
- Update when making significant changes to agent behavior
- Ensure prompts are clear and functional as standalone instructions
- Test fallback prompts periodically to ensure they work correctly

## File Format

- Plain text files (.txt)
- UTF-8 encoding
- No special formatting required
- Should be complete, standalone prompts that work without additional context
