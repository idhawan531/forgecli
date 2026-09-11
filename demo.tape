# ForgeCLI demo recording
#
#   brew install vhs
#   vhs demo.tape          # writes docs/demo.gif
#
# Records against whatever `forgecli` is on PATH, so install first:
#   pipx install .    (or: pip install -e .)

Output docs/demo.gif

Require forgecli

Set Shell "bash"
Set FontSize 18
Set Width 1400
Set Height 950
Set Theme "Catppuccin Mocha"
Set TypingSpeed 55ms
Set Padding 24

# Work in a scratch directory with a clean prompt, off camera.
Hide
Type `cd "$(mktemp -d)" && export PS1="$ " && clear`
Enter
Sleep 1s
Show

Sleep 1s

Type "forgecli templates"
Sleep 700ms
Enter
Sleep 3s

Type `forgecli generate "a react dashboard for tracking daily habits"`
Sleep 700ms
Enter
Sleep 7s

Type "cat prompts_log.md"
Sleep 700ms
Enter
Sleep 4s
