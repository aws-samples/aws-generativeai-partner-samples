# Introduction

This repo will have samples demonistrating the use of BAML from BoundaryML. Initial samples contain demonistrating Nova Act library which lets automate browser activities. So, you need to install that.
You can find more info about Nova Act here. https://github.com/aws/nova-act/tree/main

## Nova Act Setup

### Authentication

Navigate to https://nova.amazon.com/act and generate an API key.

To save it as an environment variable, execute in the terminal:
```sh
export NOVA_ACT_API_KEY="your_api_key"
```

### Installation

```bash
pip install nova-act
```

## BAML Setup
You can find instructions in setting up BAML with Python here. https://docs.boundaryml.com/guide/installation-language/python

### Install BAML

```bash
pip install baml-py
```

Once BAML is installed, run following command to generate baml_client files which are used in the client python libraries

```bash
baml-cli generate
```