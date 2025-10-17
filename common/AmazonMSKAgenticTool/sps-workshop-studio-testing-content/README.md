# Building Production Ready Agents on AWS: From Spec to Scale 

This workshop presents a comprehensive three-module approach for ISVs to build AI agents using AWS services and open-source tools. It covers Kiro IDE, Amazon Bedrock AgentCore, Strands SDK, and Model Context Protocol (MCP). Participants will gain hands-on experience building agentic capabilities from Proof of Concept (PoC) to Production deployment, with implementation-agnostic solutions supporting both SaaS and customer VPC delivery models.

## Prerequisites

1) For this workshop, we will be following the steps outlined in a Python notebook for all the modules, hence please provision a Amazon Sagemaker AI domain to use the Studio JupyterLab interactive notebook environment.
2) Clone this project and access it in the file browser of the Studio JupyterLab.
3) Open "sps-module-0-pre-req.ipynb". Complete all steps in "sps-module-0-pre-req.ipynb" notebook in SageMaker AI Studio before proceeding with the workshop modules. These prerequisite steps are mandatory.

## Module 1 - Kiro

Module 1 is a comprehensive and exploratory overview of Kiro. In this module you will build new features for your ISV's product using the agentic IDE.

In this module, we will complete 5 exercises:

Exercise 1: Agentic chat and the Vibe-coding approach  
Exercise 2: The Spec-driven approach  
Exercise 3: Yes, Kiro supports MCP Servers  
Exercise 4: Automate repetitive tasks using Agent Hooks  
Exercise 5: Guide Kiro with your custom rules and context using Steering

Now, navigate to sps-module-1-kiro.ipynb in the Amazon Sagemaker AI Notebook Studio instance and proceed with the steps specified.

## Module 2 - Strands Implementation - Amazon MSK Multi-Agent Monitoring Tool

Module 2 covers Strands SDK, our open-source SDK to build agentic solutions. In this module we will build a streamlit application that uses Strands SDK to introduce agentic AI capabilities to your observability application. As we go through this module, you will learn how to use Strands Agents SDK features and tools to easily build production-ready applications at your organization. In this usecase, we create a Observability tool - Amazon MSK monitoring streamlit application powered by multiple specialized AI agents that work together to analyze clusters, diagnose issues, and execute remediation tasks.

This Streamlit application is available as a Python notebook file "sps-module-2-strands.ipynb" in Amazon SageMaker AI Studio. Begin building the application by executing each cell sequentially to visualize the Streamlit application.

## Module 3 - Amazon Bedrock Agentcore Runtime Implementation - Amazon MSK Agentcore Monitoring Tool

Module 3 explains how you can easily and securely deploy your agentic solution at scale using Amazon Bedrock AgentCore. Amazon Bedrock AgentCore enables you to deploy and operate highly effective agents securely, at scale using any framework and model. With Amazon Bedrock AgentCore, developers can accelerate AI agents into production with the scale, reliability, and security, critical to real-world deployment. AgentCore provides tools and capabilities to make agents more effective and capable, purpose-built infrastructure to securely scale agents, and controls to operate trustworthy agents. Amazon Bedrock AgentCore services are composable and work with popular open-source frameworks and any model, so you don’t have to choose between open-source flexibility and enterprise-grade security and reliability.

In this module we will go over how you can take an AI Agent built using Strands SDK agent and deploy it on Amazon Bedrock AgentCore Runtime with just few lines of code. This module application is available as a Python notebook file "sps-module-3-agentcore.ipynb" in Amazon SageMaker AI Studio. Begin building the application by executing each cell sequentially to visualize the Streamlit application.

## On Completion

You have successfully gained comprehensive agentic implementation expertise across three focused modules:
Module 1: You implemented greenfield development using Kiro for automated spec, design and code generation from business requirements.
Module 2: You modernized existing features by leveraging Strands SDK and MCP integration, enabling seamless transition from traditional APIs to agentic architecture.
Module 3: You easily and securely deployed your AI agent using Amazon Bedrock AgentCore.

## Resource Cleanup

1) Delete the Amazon Sagemaker AI Domain created.
2) Delete any Amazon MSK clusters you have created to monitor using the applications built.
3) Delete the Amazon Bedrock Runtime Agents deployed.
4) Check for any remaining resources like IAM roles/policies in the AWS console that might not have been automatically deleted.

This cleanup process ensures you won't continue to incur charges for resources created during the workshop.

## Workshop Reference

Workshop Studio Content - Building Production Ready Agents on AWS: From Spec to Scale

**Contributors** - alwarsn@, mbay@, kurakv@, shraina@, gokhul@


