# Elastic Search Cluster Configurations Setup

After you setup Elastic Cloud on AWS cluster, you need to update the `.env` file with Elasticsearch cluster configurations. This document outlines on how to find these details for your Elstic Cloud account. The screenshots may vary at the time of configuring your specific Elasticsearch cluster but still server as a good directional instructions for the setup.

To get the API and endpoints, simply login in to Elastic cloud at https://cloud.elastic.co
Click on bread crumbs at the top left hand side to navigate to: `Elasticsearch --> Home`
Here on the top right hand corner, click on `Endpoints and API Keys`

Create an API Key and use it to configure:
- `ES_API_KEY`. 
- for `ES_URL`, skip the port `443` part. Simply provide just the URL in the format: https://{deployment-name}.es.{region}.aws.found.io

Example configurations
```
ES_URL="https://secondawsdeployment.es.us-west-1.aws.found.io"
ES_API_KEY="elo5anc1RUI1Sm9w0UcdYW5IX3A6ZnRpV2oxVVNRNE9NQU44VGljTFFSdw=="

```