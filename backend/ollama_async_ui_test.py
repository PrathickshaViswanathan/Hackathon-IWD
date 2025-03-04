import ollama
from pydantic import BaseModel
import time
import pandas as pd
import re
import os
import asyncio
from ollama import AsyncClient
import matplotlib.pyplot as plt

# Define the template
template = """
Template: (example contains ETS component statements)
Pre-condition:
1. Check variable "T5Counter" if ECU is alive or not in Trace32.
2. Connect ECU as TimeSlave over Chassis CAN Channel A.
3. Rest Bus Simulation with GlobalTime Master Implementation according to OD DBC.

Acceptance Criteria:
    Input: Send the SYNC & FUP messages with TimeDomain 0 from RBS Master on the CAN ID 0x01E as specified in OD Database.
    Output: Check the TimeBaseStatus from the variable g_timeConversionInstance.m_globalTimeStatus_u8 in Trace32.
    Expected TimeSync Status shall be 0x08/GLOBAL_TIME_BASE bit is set.
"""


async def call_model(content):
    # Formulate the prompt 
    prompt = f"""
    You are an AI expert in text pattern matching and validation.
    Your task is to compare a given content with a reference template and determine if the content follows the same structure i.e. the structure should follow the template as follows
    Pre-condition: <Extracted pre-condition statement or 'To be written by developers' if unable to extract>
    Acceptance Criteria: 
        Input: <Extracted input statement>
        Output: <Extracted output statement>
        Expected: <Extracted expected statement>


    If 'Pre-condition' is already present in the content, do not modify it. 
    Follow the below criteria when 'Pre-condition' is not available in the content: Understand 'Acceptance Criteria' and create the 'Pre-condition' from it, if possible. If unable to create content for 'Pre-condition' from 'Acceptance Criteria', 
    you should state "To be written by developers".
    Analyze 'Acceptance criteria' properly and create Input, Output and Expected. Do not put "N/A" when 'Acceptance Criteria' is available.
    ### Reference Template:
    {template}
    Above reference template is just an example format, do not use the content from reference template to create 'pre-condition'

    ### Given Content:
    {content}

    ### Task:
   
     
    1. Give the similarity percentage between template and content that aligns with any of the condition below. 
        1.1. Suppose, the content has both Pre-condition and Acceptance criteria (input/output) then similarity_percent is 100%
        1.2. Suppose, the content has Acceptance Criteria (along with input/output) but not pre-condition, then similarity_percent is 80% 
        1.3. Suppose the content has only Acceptance Criteria (there is no input/output) but not pre-condition, then similarity_percent is 50%
        1.4. Suppose the content has does not have Acceptance Criteria and pre-condition or completely different from template, then similarity_percent is less than 50%

    2. Write a suggested modifications as per the template and Provide a structured response.

    ### Response Format:
    Pre-condition:
    <Extracted or inferred Pre-condition statement>

    Acceptance Criteria:
        Input: <Extracted Input statement>
        Output: <Extracted Output statement>
        Expected: <Extracted Expected statement>

    Similarity percent:
    Similarity percentage is <calculated value>
    """

    # Query 
    response = await AsyncClient().chat(model="qwen2.5", messages=[{"role": "user", "content": prompt}], options={"temperature": 0} )

    # Print the response
    # print("======> Message <========",response['message']['content'])
    return response['message']['content']


def regex_text(text):
    # similarity_percentage_list = []
    pre_condition_match = re.search(r"Pre-condition:\s*(.*?)(?=Acceptance Criteria:)", text, re.DOTALL)
    pre_condition = pre_condition_match.group(1).strip() if pre_condition_match else None
   
    acceptance_criteria_match = re.search(r"Acceptance Criteria:\s*(?:.*?)(Input:\s*.*?\n\s*Output:\s*.*?\n\s*Expected:\s*.*)(?=Similarity percent:)", text, re.DOTALL)
    acceptance_criteria = acceptance_criteria_match.group(1).strip() if acceptance_criteria_match else None
   
    similarity_percentage_match = re.search(r"(\d+%)", text)
    similarity_percentage = similarity_percentage_match.group(1) if similarity_percentage_match else None
    
    # similarity_percentage_list.append(similarity_percentage)    #appending to add it as a column

    # print("Pre-condition:")
    # print(pre_condition)
    # print("\nAcceptance Criteria:")
    # print(acceptance_criteria)
    print("\nSimilarity percentage:", similarity_percentage)
    return pd.Series([f"""Pre-condition:{pre_condition}
                Acceptance Criteria: {acceptance_criteria}""", similarity_percentage])


def is_template_structure(value):
    if value == "80%" or  value > "80%":
        return "yes"
    elif value =="50%" or value < "50%":
        return "no"

async def process_dataframe(df, filename):
    
    # Process all rows asynchronously
    tasks = [call_model(content) for content in df["DA_Verification_Criteria"]]
    results = await asyncio.gather(*tasks)
    
    df["result"] = results
    df[["proposed_solution", "similarity_percent"]] = df["result"].apply(regex_text)
    # df["similarity_percent"] = similarity_percentage_list
    df["is_template_structure"] = df["similarity_percent"].apply(is_template_structure)
    return df


def plot_image(df):
    #matplotlib
    categories = df["is_template_structure"].value_counts().index.tolist()
    counts = df["is_template_structure"].value_counts().values.tolist()
    print("categories ", categories, " count ", counts)
    colors = ['skyblue', 'lightsalmon']
    # Create bar plot
    plt.bar(categories, counts, color=colors)

    # Customize plot
    plt.xlabel('Follows Template structure ')
    plt.ylabel('Counts')
    plt.title('Bar Graph of Categorical Feature Counts')
    #plt.xticks(rotation=45) # Rotate x-axis labels for better readability

    # Save plot to uploads directory
    plot_path = os.path.join("uploads", "plot.png")
    plt.savefig(plot_path)
    plt.close()  # Close the plot to free up memory
    return plot_path
