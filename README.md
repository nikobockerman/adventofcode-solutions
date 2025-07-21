# AdventOfCode solutions

This repository contains solvers for some Advent Of Code problems over the
years. This is a workspace for personal use where it will be easy to add
new solvers for new problems without having to bother with how to set
project up and how to run a new solver with input file and how to include
tests and tools for the solver. And for multiple programming languages
that I have desired to learn and use over the years.

This is also a personal playground for integrating with tools like CI and
keeping control of the tools used in CI and in development even when
actual coding is done only rarely.

## Architecture in the repository

Repository consists of two parts: command line tool and individual solvers.

### CLI tool

**aoc-main** directory contains a CLI tool for running individual solvers. It
launches solvers as separate processes, provides them necessary inputs and
processes their outputs. And shows the information to user.

### Solvers

One solver always implements solver for the two problem parts of that day. Each
programming language has their own directory and own way to launch one solver.
**aoc-main** contains language specific implementation which ties the tooling
of the solver together with **aoc-main**.

## API between solver executable and aoc-main

### Inputs

Solver executable is executed with 2 arguments:

1. log level as integer: 0, 1, 2
2. part number: 1, 2

Stardard input is used to pass input of the day to solver.

### Outputs

Return code tells whether the solver executed successfully or not.

Stdout must contain only the answer to the problem.

Stderr contains possible log and error messages.
