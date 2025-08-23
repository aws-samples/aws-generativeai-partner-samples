# 🎬 TwelveLabs Video Analysis Agentic AI for AgentCore Runtime

A **production-ready multi-agent AI system** for intelligent video analysis using TwelveLabs API and Elasticsearch. This system processes videos, generates embeddings, performs vector search, and provides intelligent analysis using pure TwelveLabs models.

## 🎯 What This System Provides

### **Advanced Video Analysis Pipeline**
- **TwelveLabs Integration**: Video processing with Marengo-retrieval-2.7 embeddings
- **Elasticsearch Vector Search**: High-performance similarity search with 1024-dimensional vectors
- **TwelveLabs Pegasus Analysis**: Intelligent multimodal analysis with TwelveLabs Pegasus 1.2
- **Comprehensive Reporting**: Structured analysis reports with quality assessment

### **Production-Ready Multi-Agent Architecture**
- **VideoEmbeddingAgent**: Video ingestion, validation, and embedding generation
- **VectorSearchAgent**: Search infrastructure management and vector retrieval
- **MultimodalAnalysisAgent**: Intelligent analysis and response synthesis
- **Robust Error Handling**: Fallback mechanisms for all components

## 🏗️ System Architecture

```
Video URLs → VideoEmbeddingAgent → VectorSearchAgent → MultimodalAnalysisAgent → Analysis Report
     ↓              ↓                    ↓                      ↓
TwelveLabs API → Elasticsearch → TwelveLabs Pegasus → Structured Output
```

### **Agent Pipeline Flow**
1. **🎥 VideoEmbeddingAgent**: Processes videos using TwelveLabs API and generates embeddings
2. **🔍 VectorSearchAgent**: Indexes embeddings in Elasticsearch and performs vector search
3. **🤖 MultimodalAnalysisAgent**: Analyzes results using TwelveLabs Pegasus and generates reports

## 🚀 Quick Start

### **Step 0: AWS CLI**
Make sure aws CLI is installed and configured

```bash
aws configure
```

### **Step 1: Get the System**

```bash
# Clone or download the system
cd twelevelabs-elastic-llamaindex-on-agentcore

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install bedrock-agentcore-starter-toolkit
```

### **Step 2: Configure and Launch with Bedrock AgentCore Toolkit**

```bash 
# Configure your agent for deployment
agentcore configure -e agentic_app.py

# Deploy your agent with Elastic Endpoints
agentcore launch -l --env ES_URL="https://... Your End Point ..." --env ES_CLOUD_ID="... Your Cloud ID ..." --env ES_API_KEY="... Your API Key ..."
```
### **Step 3: Set Up TwelveLabs API Key**

Store your TwelveLabs API key in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
    --name "llama-test" \
    --description "TwelveLabs API credentials" \
    --secret-string '{"TL_API_Key":"your_twelvelabs_api_key_here"}'
```

### **Step 4: Testing Your Agent Locally and on AWS**

You can test your agent locally before deploying to the cloud:

```bash
# Launch locally
agentcore launch -l --env ES_URL="https://... Your End Point ..." --env ES_CLOUD_ID="... Your Cloud ID ..." --env ES_API_KEY="... Your API Key ..."

# Invoke the agent with a query
agentcore invoke -l '{
  "prompt": "A guy in red t-shirt on a chair",
  "session_id": "3456789"
}'

#For cloud deployment, remove the -l flag:

# Deploy to cloud
agentcore launch --env ES_URL="https://... Your End Point ..." --env ES_CLOUD_ID="... Your Cloud ID ..." --env ES_API_KEY="... Your API Key ..."


# Invoke the deployed agent
agentcore invoke -l '{
  "prompt": "A guy in red t-shirt on a chair",
  "session_id": "3456789"
}'
```

### **Typical Output**
Here is how typical output would look like.

```
(venv) sripendi@80a99716627f 12labs-elastic-from-scratch % agentcore invoke -l '{
  "prompt": "A guy in red t-shirt on a chair",
  "session_id": "3456789"
}'
Payload:
{
  "prompt": "A guy in red t-shirt on a chair",
  "session_id": "3456789"
}
Invoking BedrockAgentCore agent 'agentic_app' locally
Session ID: b2e12abd-73f9-40d4-a8a5-8faf8d6fcd18

Response:
{
  "response": "\"{'query_1': {'query': 'A person with Red t-shirt sitting on a chair', 'results': {'pipeline_metadata': 
{'execution_time': '2025-08-22T22:35:00.911570', 'stages_completed': 3, 'success': True, 'videos_processed': 1, 'query': 'A 
person with Red t-shirt sitting on a chair'}, 'stage_1_video_processing': {'agent_metadata': {'agent_name': 
'VideoEmbeddingAgent', 'execution_id': 1, 'completed_at': '2025-08-22T22:35:00.911242'}, 'validation_results': 
{'validated_videos': [{'id': 0, 'url': 
'https://XXXXXXXX.s3.amazonaws.com/fast_video.mp4?AWSAccessKeyId=XXXXXXXX&Signature
=agG0HzYlFXxKODXXXXXXUVc97NKjmPMjI%3D&Expires=1755905668', 'name': 
'fast_video.mp4?AWSAccessKeyId=<AWS_ACCESS_KEY>&Signature=<SIGNATURE>&Expires=<TIMESTAMP>', 'status': 
'validated', 'validated_at': '2025-08-22T22:34:29.161353'}], 'failed_videos': [], 'total_submitted': 1, 'total_validated': 1, 
'validation_metadata': {'processed_at': '2025-08-22T22:34:29.161364', 'success_rate': 1.0}}, 'embedding_results': 
{'embedding_tasks': [{'task_id': '68a8f075a52deb365714d07f', 'video_info': {'id': 0, 'url': 
'https://XXXXXXXXX.s3.amazonaws.com/fast_video.mp4?AWSAccessKeyId=<AWS_ACCESS_KEY>&Signature=<SIGNATURE>&Expires=<TIMESTAMP>', 'name': 
'fast_video.mp4?AWSAccessKeyId=XXXXXXXX&Signature=agG0HzXXXXXXYlFXxKODUVc97NKjmPMjI%3D&Expires=1755905668', 'status': 
'validated', 'validated_at': '2025-08-22T22:34:29.161353'}, 'task_object': 
TasksRetrieveResponse(video_embedding=TasksRetrieveResponseVideoEmbedding(metadata=VideoEmbeddingMetadata(input_url='https://XXXXXXXXXXX.s3.amazonaws.com/fast_video.mp4?AWSAccessKeyId=<AWS_ACCESS_KEY>&Signature=<SIGNATURE>&Expires=<TIMESTAMP>', input_filename=None, video_clip_length=6.0, video_embedding_scope=['clip'], 
duration=28.066667), segments=[VideoSegment(float_=[0.03403221, 0.00928951, 0.010746133, 0.007694546, -0.021936007, 
-0.040870458, 0.039624173, 0.0013945994, 0.0068269693, -0.024715677, -0.017928628, -0.029789273, -0.017061668, 0.0009430023, 
0.07224765, 0.028549597, -0.06463625, -0.0067653195, 0.0006524212, 0.02615641, 0.042890012, -0.017315386, -0.016819945, 
0.038478594, 0.008319392, 0.0041188383, 0.021745393, 0.008608194,
...........
...........
...........
...........
'quality_assessment': {'overall_score': 6.82, 'quality_level': 'Medium', 'metrics': {'length_score': 3.282, 'structure_score':
8, 'content_score': 7, 'completeness_score': 9}, 'assessed_at': '2025-08-22T22:42:05.890498'}, 'recommendations': ['Review the
5 most relevant video segments for detailed content', 'Consider the key insights for further analysis or action items', 'Use 
temporal information to understand the sequence of events in the video', 'Cross-reference similarity scores to identify the 
most relevant content', 'Consider expanding the search query for more comprehensive results'], 'synthesis_metadata': 
{'report_length': 1641, 'quality_score': 6.82, 'recommendations_count': 5, 'synthesized_at': 
'2025-08-22T22:42:05.890511'}}}}}}\"

```

## 🎨 System Components

### **🎥 VideoEmbeddingAgent**

**Purpose**: Video processing and embedding generation using TwelveLabs API

**Task 1: Video Ingestion & Validation**
- Validates video URLs and accessibility
- Extracts video metadata and preprocessing
- Handles batch processing for multiple videos

**Task 2: Embedding Generation & Monitoring**
- Creates TwelveLabs embedding tasks using Marengo-retrieval-2.7
- Monitors task completion with robust polling
- Extracts 1024-dimensional embeddings from video segments

**Key Features**:
- Asynchronous task monitoring with timeout handling
- Comprehensive error handling and retry mechanisms
- Fallback embeddings for demo mode

### **🔍 VectorSearchAgent**

**Purpose**: Elasticsearch operations and vector search management

**Task 1: Index Management & Storage**
- Initializes Elasticsearch client with cloud configuration
- Creates vector indices with TwelveLabs-specific mappings
- Performs bulk indexing of video embeddings with metadata

**Task 2: Vector Search & Ranking**
- Generates query embeddings using TwelveLabs text embedding API
- Executes KNN searches with cosine similarity
- Ranks and filters results by relevance scores

**Key Features**:
- Optimized for 1024-dimensional TwelveLabs embeddings
- Scalable bulk indexing with error handling
- Advanced search result processing and ranking

### **🤖 MultimodalAnalysisAgent**

**Purpose**: Intelligent analysis using TwelveLabs Pegasus and response generation

**Task 1: Multimodal Context Processing**
- Processes video segments with textual queries using TwelveLabs Pegasus
- Handles video content analysis and understanding
- Implements model fallback strategies

**Task 2: Response Synthesis & Quality Control**
- Synthesizes responses from multiple video segments
- Generates comprehensive video analysis reports
- Assesses response quality and provides recommendations

**Key Features**:
- Pure TwelveLabs Pegasus LLM integration
- Comprehensive report generation with structured output
- Quality assessment and recommendation system


## 🔧 Configuration

### **Environment Variables**

```bash
# Elasticsearch Configuration
ES_CLOUD_ID=your_elasticsearch_cloud_id
ES_API_KEY=your_elasticsearch_api_key

# TwelveLabs API Key (stored in AWS Secrets Manager)
# Secret name: "llama-test"
# Secret key: "TL_API_Key"

# Optional: AWS Configuration for S3 video access
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
```

### **Service Requirements**

1. **TwelveLabs API**: For video processing, embeddings, and LLM analysis
2. **Elasticsearch Cloud**: For vector storage and search
3. **AWS Secrets Manager**: For secure API key storage
4. **AWS S3** (Optional): For private video storage


## 🔐 Security Best Practices

- **API Keys**: Store TwelveLabs API key in AWS Secrets Manager
- **Environment Variables**: Use environment variables for Elasticsearch credentials
- **Network Security**: Configure Elasticsearch with proper access controls
- **Input Validation**: Validate video URLs and user inputs
- **Error Handling**: Implement comprehensive error handling with fallbacks

## 💰 Cost Optimization

- **TwelveLabs**: Monitor video processing usage and optimize batch sizes
- **Elasticsearch**: Use appropriate instance sizes and storage tiers
- **AWS**: Monitor S3 usage and implement lifecycle policies
- **Monitoring**: Set up usage alerts and cost tracking


## 📞 Support and Troubleshooting

### **Common Issues**

1. **"TwelveLabs API key not found"**
   ```bash
   # Store API key in Secrets Manager
   aws secretsmanager create-secret --name "llama-test" --secret-string '{"TL_API_Key":"your_key"}'
   ```

2. **"Elasticsearch connection failed"**
   ```bash
   # Check cloud ID and API key
   export ES_CLOUD_ID=your_cloud_id
   export ES_API_KEY=your_api_key
   ```

3. **"S3 video access denied"**
   ```bash
   # Check AWS credentials and S3 permissions
   aws s3 ls s3://sripendi-twelvelabs-videos-010526247135/
   ```

### **Performance Optimization**

- **Batch Processing**: Process multiple videos in parallel
- **Caching**: Implement embedding caching for repeated videos
- **Index Optimization**: Tune Elasticsearch index settings
- **Model Selection**: Use appropriate TwelveLabs models based on use case

## 🎉 Success Metrics

Your system is working correctly when:

- ✅ Demo runs without errors in fallback mode
- ✅ Video embeddings are generated successfully with TwelveLabs
- ✅ Elasticsearch indexing completes
- ✅ Vector search returns relevant results
- ✅ TwelveLabs Pegasus analysis generates coherent reports
- ✅ Quality scores are within acceptable ranges

## 📈 What's Next?

### **Extend Your System**

1. **Add more video sources** (S3, YouTube, streaming)
2. **Implement real-time processing** for live video streams
3. **Add custom analysis models** for domain-specific insights
4. **Create visualization dashboards** for results
5. **Implement user authentication** and access controls

### **Advanced Features**

- **Multi-language support** for international content
- **Custom TwelveLabs model fine-tuning** for specialized domains
- **Workflow automation** with complex decision trees
- **Integration APIs** for external systems
- **Advanced analytics** and reporting dashboards

---

## 🏆 Conclusion

This TwelveLabs Video Analysis system provides a comprehensive, production-ready solution for intelligent video processing and analysis. The multi-agent architecture ensures scalability, maintainability, and robust error handling while delivering sophisticated video understanding capabilities using pure TwelveLabs technology.

**🎬 Start analyzing your videos with AI today!**

---

**Built with ❤️ using TwelveLabs, Elasticsearch, and LlamaIndex**
