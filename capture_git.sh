#!/bin/bash


repo=$1
pattern=$2

# Loop through each commit
git -C "$repo" tag -l "$pattern" | while read ref; do
  echo "Executing command for commit $ref"

  # Checkout to the commit
  git -C "$repo" checkout $ref

  python -m neogit init
  # Execute your command
  # python -m neogit commit "$ref" -r "$repo/xen"
  python -m neogit commit "$ref" -r "$repo/xen"

done

# Checkout to the original branch
git -C "$repo" checkout -

echo "Command executed for all commits."

