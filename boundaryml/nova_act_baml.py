from nova_act import NovaAct
from baml_client.types import AWSInfra
from baml_client.sync_client import b

with NovaAct(starting_page="https://aws.amazon.com", headless=True, record_video=True) as n:
    n.act("click on Ask AWS Chat Icon")
    n.act("ask how many regions and AZs are there in AWS. type enter and wait for reply")
    result = n.act("Provide info about AWS Infrastructure from the AI response",
                   schema=AWSInfra.model_json_schema())
    
    aws_infra = AWSInfra.model_validate(result.parsed_response)
    print(f"Regions: {aws_infra.regions}, AZs: {aws_infra.azs}")
    
    print(b.InfraQuestion(f"How many regions are there?. context: {aws_infra}"))