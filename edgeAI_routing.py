from flask import Flask, request, jsonify, Response
import json
import warnings 
warnings.filterwarnings('ignore')
from functools import lru_cache
import ollama
import sqlite3
import pandas as pd
from expertProfile import expertDataAnalystInstruction, expertSelfAnalysisInstruction, conversationalInstruction
# import shelve
from waitress import serve
import os
import gc
from tinyDBHandler import retrieveRecord, updateRecord, createRecord, tableIsExisting, removeItemFromRecord
# from pandasai.llm.local_llm import LocalLLM
# from pandasai.smart_dataframe import SmartDataframe



def get_unique_items(column_name, table_name):
    conn = sqlite3.connect('EdgeDB.db')  
    cursor = conn.cursor()
    cursor.execute(f"SELECT DISTINCT {column_name} FROM {table_name}")
    unique_items = cursor.fetchall()
    conn.close()
    return [item[0] for item in unique_items if item[0] is not None]

ManagementZone = get_unique_items('ManagementZone', 'Infra_Utilization')
Hostname = get_unique_items('Hostname', 'Infra_Utilization')
ApplicationName = get_unique_items('ApplicationName', 'Infra_Utilization')
ApplicationOwner = get_unique_items('ApplicationOwner', 'Infra_Utilization')
IPAddress = get_unique_items('IPAddress', 'Infra_Utilization')
HostAndIP = []
for index, item in enumerate(IPAddress):
    HostAndIP.append(Hostname[index] +' '+ item.replace('[', '').replace('"', '').replace(']',''))


EXPERT_PROFILE = [expertDataAnalystInstruction(), 
                  expertSelfAnalysisInstruction(ManagementZone, HostAndIP, Hostname, ApplicationName, ApplicationOwner, IPAddress),
                  conversationalInstruction()
                  ]


app = Flask(__name__)

def collectData(servers):
    try:
        if not servers:
            return None 
        with sqlite3.connect('EdgeDB.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT max(logtimestamp) FROM infra_Utilization')
            last_update_time = cursor.fetchone()[0]
            
            if not last_update_time:
                return None 
            tenMinutes_ago = (pd.to_datetime(last_update_time) - pd.Timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

            # Create a parameterized query
            placeholders = ', '.join('?' for _ in servers)
            query = f"""SELECT * FROM infra_Utilization
                        WHERE Hostname IN ({placeholders})
                        AND logtimestamp >= ?"""

            # Execute the query with parameters
            data = pd.read_sql_query(query, conn, params=(*servers, tenMinutes_ago))
            data.drop(['DiskLatency', 'ReadLatency', 'WriteLatency', 'vendor', 'OS', 'OperatingSystem', 'IPAddress', 'DriveLetter',	'ManagementZone',
                       'DataCenter', 'DatacenterRegion',	'ApplicationName',	'userIP', 'TotalMemory', 'TotalDiskSpaceGB', 'NetworkTrafficAggregate',
                       'ApplicationOwner', 'Vendor', 'CreatedAt', 'CreatedBy', 'Datacenter'], axis = 1, inplace = True, errors='ignore')
            tenMinutes_ago= None
            del tenMinutes_ago
            gc.collect()
            gc.garbage[:]
            return data
    except Exception as e:
        print(f'From edgeAI_routing, Error in collectData in collectData function:\n\t{e}')
        return None
    



def convert_to_dict():
    pref = retrieveRecord('tinyDatabase.json', 'AutoAI_server', 'servers')
    # with shelve.open('prefServers.db') as db: # Collect preferred servers
    #     if 'server' not in db:
    #         return None
    #     else:
    #         pref = db['server']

    data = collectData(pref)
    if data is not None:
        if isinstance(data, pd.DataFrame):
            output= json.dumps(data.to_dict(orient='records'))
            data = None
            del data 
            gc.collect()
            gc.garbage[:]
            return output
            # return data.to_dict(orient='records')
        elif isinstance(data, list):
            output =  [item.to_dict(orient='records') for item in data]
            data = None
            del data
            gc.collect()
            return output
        else:
            raise ValueError("Unsupported data type in convert_to_dict function in edge_AI_routing")
    else:
        return None



def tenMinutesData():
    try:
        with sqlite3.connect('EdgeDB.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT max(logtimestamp) FROM infra_Utilization')
            last_update_time = cursor.fetchone()[0]
            
            if not last_update_time:
                return None 
            tenMinutes_ago = (pd.to_datetime(last_update_time) - pd.Timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

            # Create a parameterized query
            query = f"""SELECT * FROM infra_Utilization
                        WHERE logtimestamp >= ?"""

            # Execute the query with parameters
            data = pd.read_sql_query(query, conn, params=(tenMinutes_ago,))
            data.drop(['DiskLatency', 'ReadLatency', 'WriteLatency', 'vendor', 'OS', 'OperatingSystem',
                       'DataCenter', 'DatacenterRegion',	'ApplicationName',	'userIP', 'TotalMemory',
                       'ApplicationOwner', 'Vendor', 'CreatedAt', 'CreatedBy', 'Datacenter'], axis = 1, inplace = True, errors='ignore')

            if data is not None:
                if isinstance(data, pd.DataFrame):
                    return json.dumps(data.to_dict(orient='records'))
                    # return data.to_dict(orient='records')
                elif isinstance(data, list):
                    return [item.to_dict(orient='records') for item in data]
                else:
                    raise ValueError("Unsupported data type in tenMinutesData function in edge_AI_routing")
            else:
                return None
    except Exception as e:
        print(f'From edgeAI_routing, Error in tenMinutesData function:\n\t{e}')
        return None



@app.route('/selfAnalysis_expert', methods = ['POST'])
def selfAnalysis_expert():
    """Handles the self analysis expert query"""
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"error": "Missing prompt"}), 400
    
    data_input = data['prompt']
    history = data['histories']

    memory_text = ""
    for turn in history:  # Take only last 10 turns
        role = "User" if turn['role'] == 'user' else "Assistant"
        content = turn['content']
        memory_text += f"{role}: {content}\n"
        
    profile = EXPERT_PROFILE[1]
    context_data = convert_to_dict()

    full_prompt = f"""Here is your system instruction:
        {profile}

        Here is the conversation history so far:
        {memory_text}
        """
    
    def generate_stream():
        stream = ollama.generate(
            model='gemma3',
            system=profile,
            prompt=data_input,
            options={'temperature': 0.2},
            stream=True,  # Stream must be set to True
            keep_alive=True,  # Keep the connection alive,
        )

        # Iterate through streamed response chunks
        for chunk in stream:
            text_chunk = chunk['response']
            yield f"{text_chunk}"

    return Response(generate_stream(), content_type='text/plain')


@app.route('/aiAnalysis_expert', methods=['POST'])
def aiAnalysis_expert():
    profile = EXPERT_PROFILE[0]
    data_input = convert_to_dict()
    if data_input is not None:
        def generate_stream():
            stream = ollama.generate(
                model='gemma3',
                system=profile,
                prompt=data_input,
                options={'temperature': 0.2, 'num_ctx': 8000, 'top_p': 0.9},
                stream=True 
            )

            # Iterate through streamed response chunks
            for chunk in stream:
                text_chunk = chunk['response']
                yield f"{text_chunk}"

        return Response(generate_stream(), content_type='text/plain')
    else:
        return jsonify({"error": "The selected server is not available in the database"}), 400




@app.route('/conversation_expert', methods=['POST'])
def conversational_experts():
    data = request.get_json()
    if not data or 'prompts' not in data:
        return jsonify({"error": "Missing prompt"}), 400
    
    data_input = data['prompts']
    conversation_history = data['history'] 

    memory_text = ""
    for turn in conversation_history:  # Take only last 10 turns
        role = "User" if turn['role'] == 'user' else "Assistant"
        content = turn['content']
        memory_text += f"{role}: {content}\n"

    profile = EXPERT_PROFILE[2]
    context_data = tenMinutesData()

    full_prompt = f"""{conversationalInstruction}.
    Here is the data:
        {context_data}

        Here is the conversation history so far:
        {memory_text}
        """

    if data_input is not None:
        def generate_stream():
            stream = ollama.generate(
                model='gemma3',
                system=profile + full_prompt,
                prompt=data_input,
                options={'temperature': 0.2, 'top_p': 0.9},
                stream=True,
            )
            # Iterate through streamed response chunks
            for chunk in stream:
                text_chunk = chunk['response']
                yield f"{text_chunk}"

        # data_input = None
        # del data_input
        # gc.collect()
        # gc.garbage[:]
        return Response(generate_stream(), content_type='text/plain')


@app.route('/task_router', methods = ['POST'])
def routeTask():
    """Routes the task to the appropriate function based on the expert profile type"""
    data = request.get_json()
    # if not data or 'expert_type' not in data or 'prompt' not in data:
    #     return jsonify({"error": "Missing expert_type or prompt"}), 400
    
    expert_type = data.get('expert_type')
    
    if expert_type == 'selfAnalysis':
        prompt = data['prompt']
        result = selfAnalysis_expert(prompt)
    elif expert_type == 'aiAnalysis':
        result = aiAnalysis_expert()

    return result



if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=3000, threads=8)
    # app.run(port=3000, debug=True)


# @app.route('/ask/', methods=['POST'])
# def selfAnalysis_expert():
#     data = request.get_json()
#     if not data or 'expert_type' not in data or 'prompt' not in data:
#         return jsonify({"error": "Missing expert_type or prompt"}), 400
    
#     expert_type = data['expert_type']

#     if expert_type == 'aiAnalysis':
#         profile = EXPERT_PROFILE[0]
#     elif expert_type == 'selfAnalysis':
#         profile = EXPERT_PROFILE[1]

#     try:
#         # Cache repeated identical queries
#         @lru_cache(maxsize=100)
#         def cached_generate(prompt):
#             response = ollama.generate(
#                 model='gemma3:4b',
#                 system=profile,
#                 prompt=prompt,
#                 options={'temperature': 0.2}
#             )
#             return response['response']
        
#         result = cached_generate(data['prompt'])
#         return jsonify({"response": result})
    
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# def aiAnalysis_expert():
#     """Handles the AI analysis expert query"""
#     profile = EXPERT_PROFILE[0]
#     data_input = convert_to_dict()
#     try:
#         # Cache repeated identical queries
#         @lru_cache(maxsize=100)
#         def cached_generate(prompt):
#             response = ollama.generate(
#                 model='gemma3:4b',
#                 system=profile,
#                 prompt=prompt,
#                 options={'temperature': 0.2, 'num_ctx': 8000, 'top_p': 0.9},
#                 keep_alive=True
#             )
            
#             return response['response']
        
#         result = cached_generate(data_input)
#         return jsonify({"response": result})
    
#     except Exception as e:
#         return jsonify({"error from getting the model to work": str(e)}), 500