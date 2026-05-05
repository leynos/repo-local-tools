Feature: Manage local agent tools
  Repository maintainers install shared agent tool definitions into the current
  repository and then update or commit those managed files explicitly.

  Scenario: Install an MCP server for supported clients
    Given a git repository workspace
    And an MCP registry definition named "echo"
    When I run "repo-local-tools mcp install echo"
    Then the command succeeds
    And the repository has MCP configuration for "echo" in every supported client
    And ".gitignore" ignores generated MCP configuration

  Scenario: Install a skill from the shared registry
    Given a git repository workspace
    And a skill registry directory named "reviewer"
    When I run "repo-local-tools skill install reviewer"
    Then the command succeeds
    And the repository has skill "reviewer" in every supported client
    And ".gitignore" ignores generated skill directories

  Scenario: Update all managed tools
    Given a git repository workspace
    And an installed MCP server named "echo"
    And an installed skill named "reviewer"
    When I change the MCP registry definition named "echo"
    And I change the skill registry directory named "reviewer"
    And I run "repo-local-tools mcp update"
    Then the command succeeds
    When I run "repo-local-tools skill update"
    Then the command succeeds
    And the repository has updated MCP configuration for "echo"
    And the repository has updated skill "reviewer"

  Scenario: Load all local tool sources into the shared registry
    Given a git repository workspace
    And a local skill source named "reviewer"
    And a local MCP JSON configuration for "echo"
    When I run "repo-local-tools load"
    Then the command succeeds
    And the shared registry has skill "reviewer"
    And the shared registry has MCP server "echo"

  Scenario: Commit a managed MCP server
    Given a git repository workspace
    And an installed MCP server named "echo"
    When I run "repo-local-tools mcp commit echo"
    Then the command succeeds
    And git contains a commit with subject "Install MCP server echo"
