import requests
import json
from thefuzz import fuzz
from credentials import TENANT, API_KEY


tenant = 'xxxxx'
api_key = 'xxxxxxx' 
get_host_url = tenant + '/api/v2/entities?entitySelector=type%28HOST%29'
get_host_info_url_base = tenant + '/api/v2/entities/'


headers = {'accept': 'application/json', 'charset':'utf-8', 'Authorization': api_key}


#use the dynatrace api to get a list of all the hosts monitored
def get_all_hosts():
    r = requests.get(get_host_url, headers=headers)
    all_hosts = r.json()

    #Get a list of all hosts in a tenant
    host_id_list = []
    for host in all_hosts['entities']:
        host_id_list.append(host['entityId'])
    return host_id_list

#manually parse the OS strings to match the AWS requirements
#print out if found a new string 
def parse_OSVersion_Distribution(os_string):
   if ("Ubuntu" in os_string):
       os_split = os_string.split(" ")
       version_split = os_split[1].split(".")
       os_version = os_split[0] + " " + version_split[0] + "." + version_split[2]
       return {"OSVersion": os_version, "OSDistribution": os_split[0]} 
   if ("Red Hat Enterprise Linux CoreOS" in os_string):
        os_split = os_string.split(" ")
        dot_split = os_split[5].split(".")
        version = dot_split[0]
        new_version = version[:1] + "." + version[1:]
        new_version_string = "RHCOS" + " " + new_version
        return {"OSVersion": new_version_string, "OSDistribution": "RHCOS"}
   if ("Windows Server" in os_string):
       os_split = os_string.split(" ")
       new_version = os_split[0] + " " + os_split[1] + " " + os_split[2]
       return {"OSVersion": new_version, "OSDistribution": "Windows Server"}
   if ("Container-Optimized OS" in os_string):
       os_split = os_string.split(" ")
       split_dot = os_split[4].split(".")
       new_version = "COS " + split_dot[0] + "." +split_dot[1]
       return {"OSVersion": new_version, "OSDistribution": "COS"}
   if ("Amazon Linux 2" in os_string):
       os_split = os_string.split(" ")
       split_dot = os_split[4].split(".")
       new_version = "AL2 " + split_dot[0] + "." + split_dot[1]
       return {"OSVersion": new_version, "OSDistribution": "AL2"}
   if ("z/OS" in os_string):
       os_split = os_string.split(" ")
       new_version = os_split[0] + " " + os_split[2]
       return {"OSVersion": new_version, "OSDistribution": "z/OS"}
   if ("AIX" in os_string):
       os_split = os_string.split(" ")
       new_version = "AIX " + os_split[2]
       return {"OSVersion": new_version, "OSDistribution": "AIX"} 
   else:
       print("NEW OS STRING")
       print(os_string)

#parse out all the host information
def process_hosts(host_id_list):
    process_group_ids = []
    host_details_list = []
    unprocessable_hosts = []
    for host in host_id_list:
        get_host_info_url =  get_host_info_url_base + host
        host_details_response = requests.get(get_host_info_url, headers=headers)
        host_details_body = host_details_response.json()

        host_object = {}
        try:
            if host_details_body['properties']["state"] != "MONITORING_DISABLED":
                host_object['ResourceType'] = "SERVER"
                host_object['ResourceName'] = host_details_body['displayName']
                host_object['ResourceId'] = host_details_body['entityId']
                host_object['IpAddress'] = host_details_body['properties']['ipAddress'][0]
                host_object['HostName'] = host_details_body['displayName']

                host_object['CPUArchitecture'] = host_details_body['properties']['bitness'] + "bit"
                
                os_version = host_details_body['properties']['osVersion']
                os_parsed = parse_OSVersion_Distribution(os_version)
                host_object['OSDistribution'] = os_parsed['OSDistribution']
                host_object['OSVersion'] = os_parsed['OSVersion']
                host_object['OSType'] = host_details_body['properties']['osType'].capitalize()

                to_relationships = host_details_body['toRelationships']
                for process_group in to_relationships['isProcessOf']:
                    if process_group['type'] == 'PROCESS_GROUP_INSTANCE':
                        process_group_ids.append(process_group['id'])
        except Exception as error:
                print("Error in " + host)
                print (error)
                
        if not host_object:
            unprocessable_hosts.append(host)
        else:
            host_details_list.append(host_object)

    print("UNPROCESSABLE")
    print(unprocessable_hosts)
    return {"host_details" :host_details_list, "process_groups": process_group_ids}


#go through and parse all the processes 
def process_process_groups(process_group_ids, aws_library):
    pgi_instances = []
    count = 0
    for p_g_inst in process_group_ids:
        count = count + 1
        print(count)

        get_pgi_info_url =  get_host_info_url_base + p_g_inst
        pgi_details_response = requests.get(get_pgi_info_url, headers=headers)
        pgi_details_body = pgi_details_response.json()

        pgi_properties = pgi_details_body["properties"]

        pgi_object = {}
        pgi_object['ResourceType'] = 'PROCESS'
        pgi_object['ResourceName'] = pgi_details_body['displayName']
        pgi_object['ResourceId'] = pgi_details_body['entityId']
        pgi_object['AssociatedServerIds'] = []

        try:
            #adjust for GO vs MONGO
            if "processType" in pgi_properties and pgi_properties["processType"] == "GO":
                    pgi_object['ApplicationType'] = "GO"
            elif "softwareTechnologies" in pgi_properties:
                softwareTechnologies = pgi_properties["softwareTechnologies"]
                for software in softwareTechnologies:
                    for application_type in aws_library["ApplicationType"]:
                        fuzz_score = fuzz.partial_ratio(software['type'].lower(), application_type.lower())
                        if fuzz_score > 80:
                            #accounting for generic java case
                            if not ('ApplicationType' in pgi_object and (pgi_object['ApplicationType'] == "Tomcat" or pgi_object['ApplicationType'] == "Spring")):
                                pgi_object['ApplicationType'] = application_type
                    for language in aws_library["ProgrammingLanguage"]:
                        fuzz_score = fuzz.partial_ratio(software['type'].lower(), language.lower())
                        if fuzz_score > 80:
                                pgi_object['ProgrammingLanguage'] = language
                    if 'ApplicationType' not in pgi_object:
                            if "processType" in pgi_properties:
                                pgi_object['ApplicationType'] = pgi_properties["processType"]

            for hosts in pgi_details_body['fromRelationships']['isProcessOf']:
                pgi_object['AssociatedServerIds'].append(hosts['id'])

            if 'ApplicationType' in pgi_object:
                pgi_instances.append(pgi_object)

        except Exception as error:
                print("Error in " + pgi_details_body['entityId'])
                print (error)
                
            

    return pgi_instances                 
        


#call all the functions
host_list = get_all_hosts()
host_output = process_hosts(host_list)
host_details = host_output["host_details"]
process_group_ids = host_output["process_groups"]

aws_library = {}
with open("AWS_Valid_Values.json", "r") as infile:
        aws_library = json.load(infile) 

process_details = process_process_groups(process_group_ids, aws_library)

output_file = {"ImportFormatVersion": 1, "Resources": []}
master_list = host_details + process_details
output_file["Resources"] = master_list


with open("dynatrace_migration_data.json", "w") as outfile:
    json.dump(output_file, outfile)
