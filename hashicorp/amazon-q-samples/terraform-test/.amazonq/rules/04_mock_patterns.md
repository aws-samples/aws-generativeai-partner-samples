# Terraform Mock Patterns

## Data Source Mocking
```hcl
mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = {
      names = ["us-east-1a", "us-east-1b", "us-east-1c"]
      state = "available"
    }
  }
  
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }
  
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"vpc-flow-logs.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"
    }
  }
}
```

## Standard Provider Mocks
```hcl
mock_provider "primary_provider" {
  mock_resource "identity_resource" {
    defaults = {
      account_id = "123456789012"
      arn        = "arn:provider:service::123456789012:resource"
    }
  }
  
  mock_resource "random_resource" {
    defaults = {
      result = "mockrandom123"
      id     = "mockrandom123"
    }
  }
}
```

## Multi-Provider Mocks
```hcl
mock_provider "secondary_provider" {
  mock_resource "secondary_resource_type" {
    defaults = {
      id   = "mock-resource"
      name = "mock-resource"
      arn  = "arn:provider:service:region:123456789012:resource/mock-resource"
    }
  }
}
```

## Advanced Mock Patterns

### Random Provider Mocking
```hcl
mock_provider "random" {
  mock_resource "random_string" {
    defaults = {
      result = "mockrandom123"
      id     = "mockrandom123"
    }
  }
}
```


### External Data Source Mocking
```hcl
mock_provider "external" {
  mock_data "external" {
    defaults = {
      result = {
        "key1" = "value1"
        "key2" = "value2"
      }
    }
  }
}
```

### Complex Resource Mocking
```hcl
mock_provider "aws" {
  mock_resource "aws_s3_bucket" {
    defaults = {
      id     = "mock-bucket"
      bucket = "mock-bucket"
      arn    = "arn:aws:s3:::mock-bucket"
    }
  }
  
  mock_resource "aws_iam_role" {
    defaults = {
      id   = "mock-role"
      name = "mock-role"
      arn  = "arn:aws:iam::123456789012:role/mock-role"
    }
  }
}
```

## Key Principles
- Mock external dependencies for predictable test data
- Use consistent mock values across tests
- Provide defaults for computed attributes
- Handle multi-provider scenarios
- Mock complex resources with realistic ARN patterns
- Include all required attributes for resource validation
