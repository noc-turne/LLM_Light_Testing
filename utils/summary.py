from datetime import datetime
import pandas as pd
import os


def model_summary_table(
    eval_dict, save_path
):  # get the ealiest start time, the latest end time, total_prompt_num, total_decode_num, total_decode_speed for every model
    model_summary = {}

    for file, model_list in eval_dict.items():
        for record in model_list:
            model_name = record["model"]
            if record["start_time"] == -1:
                continue
            start_time = datetime.fromisoformat(record["start_time"])
            end_time = datetime.fromisoformat(record["end_time"])

            if model_name not in model_summary:
                model_summary[model_name] = {
                    "earliest_start": start_time,
                    "latest_end": end_time,
                    "total_prompt_num": record['prompt_token_len'],
                    "total_decode_num": record['decode_token_len'],
                    'latest_start': start_time,
                    'earliest_end': end_time
                }
            else:
                model_summary[model_name]["earliest_start"] = min(
                    model_summary[model_name]["earliest_start"], start_time
                )
                model_summary[model_name]["latest_end"] = max(model_summary[model_name]["latest_end"], end_time)
                # model_summary[model_name]["earliest_end"] = min(model_summary[model_name]["earliest_end"], end_time)
                # model_summary[model_name]["latest_start"] = max(model_summary[model_name]["latest_start"], start_time)
                model_summary[model_name]['total_prompt_num'] += record['prompt_token_len']
                model_summary[model_name]['total_decode_num'] += record['decode_token_len']

    for model_name, summary_item in model_summary.items():
        summary_item['total_runtime'] = (summary_item['latest_end'] - summary_item['earliest_start']).total_seconds()
        summary_item['decode_speed'] = summary_item['total_decode_num'] / summary_item['total_runtime'] if summary_item[
            "total_runtime"] > 0 else -1
        # print(model_name, summary_item['earliest_start'], summary_item['latest_start'], summary_item['earliest_end'], summary_item['latest_end'])

    data = []
    for model_name, summary_item in model_summary.items():
        data.append(
            {
                "Model": model_name,
                "Total Prompt Tokens": summary_item["total_prompt_num"],
                "Total Decode Tokens": summary_item["total_decode_num"],
                "Total Runtime (s)": round(summary_item["total_runtime"], 2),
                "Decode Speed (Tokens / s)": round(summary_item["decode_speed"], 2)
                if summary_item["decode_speed"] != -1 else -1
            }
        )

    df = pd.DataFrame(data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"model_summary_table_{timestamp}.xlsx"
    output_file_path = os.path.join(save_path, file_name)

    df.to_excel(output_file_path, index=False)


def file_summary_table(eval_dict, save_path):
    data = []
    for prompt, entries in eval_dict.items():
        for entry in entries:
            data.append(
                {
                    'Prompt': prompt,
                    'Model': entry['model'],
                    'Prompt Token Length': entry['prompt_token_len'],
                    'Decode Token Length': entry['decode_token_len'],
                    'Elapsed Time(s)': entry['elapsed_time']
                }
            )

    df = pd.DataFrame(data)

    df['Decode Speed(Token / s)'] = df.apply(
        lambda row: round(row['Decode Token Length'] / row['Elapsed Time(s)'], 2)
        if row['Decode Token Length'] != -1 and row['Elapsed Time(s)'] > 0 else -1,
        axis=1
    )

    df['Elapsed Time(s)'] = df['Elapsed Time(s)'].apply(lambda x: round(x, 3) if x >= 0 else x)

    df_display = df.copy()
    df_display.loc[df_display.duplicated(subset=['Prompt']), 'Prompt'] = ''

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"file_summary_table_{timestamp}.xlsx"

    output_file_path = os.path.join(save_path, file_name)
    df_display.to_excel(output_file_path, index=False)