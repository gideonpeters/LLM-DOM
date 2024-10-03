import pandas as pd
import os
import json
import csv

original_reports_path = "lh-reports/original/full/2024-08-13_15-40-23"
llm_modified_reports_path = "lh-reports/llm-modified/full/2024-08-19_11-18-35"

original_reports_output = "original_reports_output.csv"
llm_modified_reports_output = "llm_modified_reports_output.csv"

filtered_original_reports = []
filtered_llm_modified_reports = []


def create_base_csvs(): 
    original_reports = []
    llm_modified_reports = []

    for filename in os.listdir(original_reports_path):
        if filename.endswith(".json"):
            formatted_filename = filename.replace(".json", "")

            with open(os.path.join(original_reports_path, filename), 'r') as file:
                audits = json.load(file)["audits"]
            
                original_reports.append({
                    "filename": formatted_filename,
                    "audits": audits
                })

    for filename in os.listdir(llm_modified_reports_path):
        if filename.endswith(".json"):
            formatted_filename = filename.replace(".json", "")

            with open(os.path.join(llm_modified_reports_path, filename), 'r') as file:
                audits = json.load(file)["audits"]

                llm_modified_reports.append({
                    "filename": formatted_filename,
                    "audits": audits
                })


    original_reports_df = pd.DataFrame(original_reports)
    llm_modified_reports_df = pd.DataFrame(llm_modified_reports)

    original_reports_df["audits"] = original_reports_df["audits"].apply(json.dumps)
    llm_modified_reports_df["audits"] = llm_modified_reports_df["audits"].apply(json.dumps)

    original_reports_df.to_csv("original_reports_output.csv", index=False)
    llm_modified_reports_df.to_csv("llm_modified_reports_output.csv", index=False)

    print("CSVs created successfully.")

def create_filtered_csvs():
    original_reports_df = pd.read_csv(original_reports_output)
    llm_modified_reports_df = pd.read_csv(llm_modified_reports_output)

    reports_to_exclude = ["amazon", "ubereats", "glassdoor", "ziprecruiter", "behance"]

    original_reports_df = original_reports_df[~original_reports_df["filename"].str.contains("|".join(reports_to_exclude))]
    llm_modified_reports_df = llm_modified_reports_df[~llm_modified_reports_df["filename"].str.contains("|".join(reports_to_exclude))]

    """
    Filter out the audits that are not applicable ie: 
        - audits with scoreDisplayMode as notApplicable
        - audits with scoreDisplayMode as binary and score as 1
        - audits with scoreDisplayMode as informative
        - audits with scoreDisplayMode as manual
        - audits with scoreDisplayMode as metricSavings and score as 1
        - audits with scoreDisplayMode as numeric and score as 1
    """
    original_reports_df["audits"] = original_reports_df["audits"].apply(json.loads)
    llm_modified_reports_df["audits"] = llm_modified_reports_df["audits"].apply(json.loads)

    for index, row in original_reports_df.iterrows():
        audits = row["audits"]
        filtered_report = {}
        for audit_key, audit in audits.items():
            if audit['scoreDisplayMode'] != 'notApplicable':
                if ((audit['scoreDisplayMode'] == 'binary' and audit['score'] == 1) or  
                    (audit['scoreDisplayMode'] == 'informative') or  
                    (audit['scoreDisplayMode'] == 'manual') or  
                    (audit['scoreDisplayMode'] == 'error') or
                    (audit['scoreDisplayMode'] == 'metricSavings' and audit['score'] == 1) or 
                    (audit['scoreDisplayMode'] == 'numeric' and audit['score'] == 1)):
                    continue
                filtered_report[audit_key] = audit

        filtered_original_reports.append({
            "filename": row["filename"],
            "audits": filtered_report
        })

    filtered_original_reports_df = pd.DataFrame(filtered_original_reports)
    filtered_original_reports_df["audits"] = filtered_original_reports_df["audits"].apply(json.dumps)

    filtered_original_reports_df.to_csv("filtered_original_reports_output.csv", index=False)

    for index, row in llm_modified_reports_df.iterrows():
        audits = row["audits"]
        filtered_report = {}
        for audit_key, audit in audits.items():
            if audit['scoreDisplayMode'] != 'notApplicable':
                if ((audit['scoreDisplayMode'] == 'binary' and audit['score'] == 1) or  
                    (audit['scoreDisplayMode'] == 'informative') or  
                    (audit['scoreDisplayMode'] == 'manual') or  
                    (audit['scoreDisplayMode'] == 'metricSavings' and audit['score'] == 1) or 
                    (audit['scoreDisplayMode'] == 'numeric' and audit['score'] == 1)):
                    continue
                filtered_report[audit_key] = audit

        filtered_llm_modified_reports.append({
            "filename": row["filename"],
            "audits": filtered_report
        })

    filtered_llm_modified_reports_df = pd.DataFrame(filtered_llm_modified_reports)
    filtered_llm_modified_reports_df["audits"] = filtered_llm_modified_reports_df["audits"].apply(json.dumps)

    filtered_llm_modified_reports_df.to_csv("filtered_llm_modified_reports_output.csv", index=False)

    print("Filtered CSVs created successfully.")

    return filtered_llm_modified_reports_df, filtered_original_reports_df

def analyse_audit_type_frequencies(filtered_llm_modified_reports_df, filtered_original_reports_df):
    # Show the frequency of unique audits in the filtered llm modified and original reports using pandas

    filtered_llm_modified_reports_df["audits"] = filtered_llm_modified_reports_df["audits"].apply(json.loads)
    filtered_original_reports_df["audits"] = filtered_original_reports_df["audits"].apply(json.loads)

    original_audit_keys = []
    llm_modified_audit_keys = []

    for index, row in filtered_original_reports_df.iterrows():
        audits = row["audits"]
        for audit_key in audits:
            original_audit_keys.append(audit_key)

    for index, row in filtered_llm_modified_reports_df.iterrows():
        audits = row["audits"]
        for audit_key in audits:
            llm_modified_audit_keys.append(audit_key)

    original_audit_keys_df = pd.DataFrame(original_audit_keys, columns=["audit_key"])
    llm_modified_audit_keys_df = pd.DataFrame(llm_modified_audit_keys, columns=["audit_key"])

    # store the frequencies in a csv file
    original_audit_keys_df["audit_key"].value_counts().to_csv("original_audit_frequencies.csv")
    llm_modified_audit_keys_df["audit_key"].value_counts().to_csv("llm_modified_audit_frequencies.csv")

    print("Frequency Analysis complete.")

def analyse_differences_in_audits(filtered_llm_modified_reports_df, filtered_original_reports_df):
    # Show the differences in audits between the filtered llm modified and original reports using pandas

    # filtered_llm_modified_reports_df["audits"] = filtered_llm_modified_reports_df["audits"].apply(json.loads)
    # filtered_original_reports_df["audits"] = filtered_original_reports_df["audits"].apply(json.loads)

    llm_modified_audit_keys = []
    original_audit_keys = []

    for index, row in filtered_llm_modified_reports_df.iterrows():
        audits = row["audits"]
        for audit_key in audits:
            llm_modified_audit_keys.append(audit_key)

    for index, row in filtered_original_reports_df.iterrows():
        audits = row["audits"]
        for audit_key in audits:
            original_audit_keys.append(audit_key)

    
    # Create DataFrames for audit keys
    llm_modified_audit_keys_df = pd.DataFrame(llm_modified_audit_keys, columns=["audit_key"])
    original_audit_keys_df = pd.DataFrame(original_audit_keys, columns=["audit_key"])

    # Count occurrences of each audit_key and the difference_between the two
    llm_modified_counts = llm_modified_audit_keys_df.groupby("audit_key").size().reset_index(name='llm_modified_count')
    original_counts = original_audit_keys_df.groupby("audit_key").size().reset_index(name='original_count')

    # Merge counts to compare
    comparison_df = pd.merge(original_counts, llm_modified_counts, on="audit_key", how="outer").fillna(0)
    comparison_df['difference'] = comparison_df['original_count'] - comparison_df['llm_modified_count']

    # Store comparison in a file
    comparison_df.to_csv("audit_differences.csv", index=False)

    # For how many audits are the counts positively different?
    positive_difference = comparison_df[comparison_df["difference"] > 0].shape[0]
    print(f"Number of audits with positive difference: {positive_difference}")

    # Store positive difference audits in a file
    comparison_df[comparison_df["difference"] > 0].to_csv("positive_difference_audits.csv", index=False)

    # For how many audits are the counts negatively different?
    negative_difference = comparison_df[comparison_df["difference"] < 0].shape[0]
    print(f"Number of audits with negative difference: {negative_difference}")

    # Store negative difference audits in a file
    comparison_df[comparison_df["difference"] < 0].to_csv("negative_difference_audits.csv", index=False)

    # For how many audits are the counts the same?
    no_difference = comparison_df[comparison_df["difference"] == 0].shape[0]
    print(f"Number of audits with no difference: {no_difference}")

    # Store no difference audits in a file
    comparison_df[comparison_df["difference"] == 0].to_csv("no_difference_audits.csv", index=False)

    # Audit with the highest difference, show both the key name and the difference
    max_difference = comparison_df["difference"].max()
    max_difference_audit = comparison_df[comparison_df["difference"] == max_difference]
    print(f"Audit with the highest difference: {max_difference_audit}") 

    print("Difference Analysis complete.")

def main():
    create_base_csvs()
    filtered_llm_modified_reports_df, filtered_original_reports_df = create_filtered_csvs()

    analyse_audit_type_frequencies(filtered_llm_modified_reports_df, filtered_original_reports_df)

    analyse_differences_in_audits(filtered_llm_modified_reports_df, filtered_original_reports_df)

if __name__ == "__main__":
    main()


