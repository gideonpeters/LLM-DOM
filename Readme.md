#  Are Large Language Models Good Software Librarians? 

Abstract:

Performance engineering plays a vital role in web development, ensuring that web pages run smoothly in production. This involves following best practices to improve the user experience by speeding up page rendering, making interactions seamless, and preventing hardware overloads that can make pages unresponsive. However, web performance optimization can be time-consuming for developers, who often have to manually address issues uncovered during performance analysis. Automating this process could save developers time, allowing them to focus on other important tasks and speeding up the delivery of performant features to users. 
Following recent advancements in Large Language Models (LLMs), this paper evaluates the effectiveness of GPT-4o in automating the resolution of web performance issues. For this purpose, we extract the DOM trees of 15 popular websites in production (e.g., Facebook) and generate performance reports using Lighthouse. We then feed the audits in the generated reports along with the corresponding DOM trees into GPT-4o to locate and resolve the performance issues. Finally, we regenerate performance reports for the updated DOM trees, assessing if and how the performance issues are resolved. Our study lays the groundwork for automating web performance issue resolution using LLMs, offering insights into these models' HTML understanding for web performance tasks. Additionally, we provide a dataset of over 200 HTML chunks, split into more than 3,000 prompts, covering 67 different Lighthouse audit types for web performance tasks.

##  Directories

`final_dataset.zip` - contains originally extracted DOMs, their chunks, lighthouse reports of original DOMs, lighthouse reports of modified DOMs, prompts and response times of all experiments.

`scripts_and_data.zip` includes the following directories:

* **data**
    * **processed_data** (directory containing processed data for chatgpt and human generated code)
    * **raw_data** (directory containing raw data)
* **scripts** (directory containing scripts used in the project)
    * **code_generator.py** (prompt creation and code generation using GPT-3.5 Turbo)
    * **data_preprocessing.py** (extracts and pre-processes the questions and accepted code snippets from the pickle files)
    * **doctor.py** (categorizes libraries into standard, third-party, or other)
    * **hospital.py** (pipeline to execute nurse, doctor, and psychiatrist sequentially)
    * **lib_io_dependencies.py** (extracts the dependencies of libraries using the libraries.io api)
    * **lib_io_metadata.py** (extracts various metadata of libraries using the libraries.io api)
    * **lib_io_published_date.py** (extracts published dates of libraries using the libraries.io api)
    * **nurse.py** (extracts import statements from the code snippets, always returns the parent)
    * **psychiatrist.py** (identifies deprecated libraries or libraries explicitly mentioned in the question)
* **README.md** (the file you are currently reading)

##  Getting Started

`pip install -r requirements.txt`

##  Data preparation (raw_data)

The `pickle` files in the `raw_data` directory contain the raw dataset. 

`data_preprocessing.py` extracts the code and the questions to `raw_code_snippets.csv` (the accepted code) and `raw_questions.csv`. Then, it identifies and selects questions for which the corresponding accepted code contains at least one import statement (`import_code_snippets.csv`, `import_questions.csv`).

The code used for the analysis in this paper is in `chatgpt_output.zip`. This contains text files named after the Stack Overflow question ID. Each text file contains the question, the prompt, the accepted code snippet, and ChatGPT-generated code. These files were generated with `code_generator.py`. 

## Analysis (processed_data)

Note: The analysis presented below is for ChatGPT-generated code, but we repeated the same process for human-generated code using the same scripts. 

`hospital.py` will sequentially execute the scripts `nurse.py`, `doctor.py`, and `psychiatrist.py`. 

`nurse.py` - Extracts the import statements from `import_code_snippets.csv`, then extracts the libraries from `import_statements.csv`.  
* Input: `import_code_snippets.csv`
* Output: `llm_triaged_libs.csv`

`doctor.py` - Determines if a library is a standard Python library or a third-party library. If the library is neither, it is categorized as "None". 
* Input: `triaged_libs.csv`
* Output: `llm_diagnosed_libs.csv`

`psychiatrist.py` - Determines if "None" libraries are deprecated or hard-coded in the question. 
* Input: `llm_diagnosed_libs.csv`
* Output: `llm_psych_report.csv`

The scripts `lib_io_dependencies.py`, `lib_io_metadata.py`, and `lib_io_published_date.py` are scripts to mine the metadata of the third-party libraries. 

```sh
    docker run --shm-size=1g -dit -p 8000:8000 report-generator
```