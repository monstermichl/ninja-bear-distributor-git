# ninja-bear-distributor-git
This [ninja-bear](https://pypi.org/project/ninja-bear) plugin adds the distributor support for Git.

```yaml
distributors:  # Specifies which distributor plugins to load.
  # -------------------------------------------------------------------------
  # Property description for ninja-bear-distributor-git.
  #
  # distributor (required): ninja-bear-distributor-git or git
  # as          (required): Specifies how the distributor will be referenced
  #                         at the language level (in this case git).
  # url         (required): Specifies the repository's URL.
  # path        (optional): Specifies the path within the repository. If no
  #                         Path is provided, the config is added to the
  #                         root directory.
  # user        (optional): Specifies the Git user. If the user attribute,
  #                         but no value is given, the user is prompted to
  #                         provide the user attribute at runtime.
  # password    (optional): Specifies the Git password. If the password,
  #                         attribute but no value is given, the user is
  #                         prompted to provide the password attribute at
  #                         runtime.
  # branch      (optional): Specifies with which branch to work with.
  # message     (optional): Specifies the commit message. If no message got
  #                         provided, the user will be prompted to provide
  #                         a commit message at runtime.
  # ignore      (optional): If true, the section gets ignored.
  # -------------------------------------------------------------------------
  - distributor: ninja-bear-distributor-git
    as: git
    url: https://github.com/exampleuser/example-repo.git
    path: config
    user:
    password:
    branch: main
    message: Update config

languages:
  - language: ninja-bear-language-examplescript
    distributors:  # Specifies which distributor plugins to use for the language.
      - git

properties:
  - type: bool
    name: myBoolean
    value: true

  - type: int
    name: myInteger
    value: 142

  - type: float
    name: myFloat
    value: 322f  # Float with float specifier. However, an additional specifier (f) is not required and will be trimmed.

  - type: float
    name: myCombinedFloat
    value: ${myInteger} * ${myFloat}  # Number and boolean combinations get evaluated during the dump process.

  - type: double
    name: myDouble
    value: 233.9

  - type: string
    name: myString
    value: Hello World
    hidden: true  # If a property should act as a helper but should not be written to the generated file, it must be marked as 'hidden'.

  - type: regex
    name: myRegex
    value: Test Reg(E|e)x
    comment: Just another RegEx.  # Variables can be described using the comment property.

  - type: string
    name: mySubstitutedString
    value: Sometimes I just want to scream ${myString}!  # To use the value of another property, simply use its name with ${}. E.g., ${myString}.
```
