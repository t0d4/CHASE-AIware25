import argparse
import datetime
import re
import textwrap
from itertools import chain
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from langchain.chat_models.base import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from chase import DetectorAgentState, SourceCode, create_global_agents_graph


def prepare_llms(
    llm_runner: Literal["ollama", "sglang"], low_memory_mode: bool
) -> tuple[BaseChatModel, BaseChatModel, BaseChatModel]:
    if low_memory_mode:
        # use the same LLM for all roles to reduce required memory
        llm = ChatOllama(
            model="qwen3:4b",
            name="qwen3:4b",
            reasoning=True,
            num_ctx=32768,  # lower this to further reduce the memory footprint
        )
        return llm, llm, llm
    elif llm_runner == "ollama":
        supervisor_llm = ChatOllama(
            model="qwen3:32b",
            name="qwen3:32b",
            reasoning=True,
            num_ctx=20480,
        )
        workers_llm = ChatOllama(
            model="qwen3:8b",
            name="qwen3:8b",
            reasoning=True,
            num_ctx=32768,
        )
        formatter_llm = ChatOllama(
            model="gemma3:4b",
            name="gemma3:4b",
            reasoning=True,
            num_ctx=8192,
        )
        return supervisor_llm, workers_llm, formatter_llm
    elif llm_runner == "sglang":
        supervisor_llm = ChatOpenAI(
            model="Qwen/Qwen3-32B",
            name="Qwen/Qwen3-32B",
            base_url="http://127.0.0.1:30000",
            api_key="sk-dummy",  # type: ignore
        )
        workers_llm = ChatOpenAI(
            model="Qwen/Qwen3-8B",
            name="Qwen/Qwen3-8B",
            base_url="http://127.0.0.1:30001",
            api_key="sk-dummy",  # type: ignore
        )
        # llm for structured output
        formatter_llm = ChatOpenAI(
            model="google/gemma-3-4b-it",
            name="google/gemma-3-4b-it",
            base_url="http://127.0.0.1:30002",
            api_key="sk-dummy",  # type: ignore
        )
        return supervisor_llm, workers_llm, formatter_llm
    else:
        raise ValueError(f"parameter `llm_runner` got unexpected value: {llm_runner}")


def omit_middle_code_when_necessary(code: str) -> str:
    return (
        code
        if len(code) < 8000
        else code[:8000]
        + textwrap.dedent("""\
            \n
            ######################################################################
            # the lines below are omitted because they are too long for analysis. #
            ######################################################################\n
            """)
    )


def collect_codes_for_pyfile(python_filepath: Path) -> list[SourceCode]:
    python_code = python_filepath.read_text()
    source_codes = [
        SourceCode(
            filename=python_filepath.name,
            code=omit_middle_code_when_necessary(python_code),
        )
    ]
    match python_filepath.name:
        case "setup.py":
            # setup.py is usually independent
            return source_codes
        case _:
            # other cases including __init__.py
            IMPORT_PATTERN = r"^\s*import (?P<standalone_imported>[^#\s]+)"
            import_patterns = [
                m.groups()
                for m in re.finditer(IMPORT_PATTERN, python_code, flags=re.MULTILINE)
            ]
            FROM_IMPORT_PATTERN = (
                r"^\s*from (?P<import_from>[^\s]+) import (?P<imported>[^#\s]+)"
            )
            from_import_patterns = [
                m.groups()
                for m in re.finditer(
                    FROM_IMPORT_PATTERN, python_code, flags=re.MULTILINE
                )
            ]
            all_possible_modules = set()
            for ip in import_patterns + from_import_patterns:
                for item in ip:
                    all_possible_modules.add(
                        item.split(".")[-1]
                    )  # from aaa.bbb.ccc import xyz => ccc, xyz
            # search for python files
            for possible_module_name in all_possible_modules:
                if possible_module_name == "*":
                    # wildcard import pattern
                    continue

                module_paths = list(
                    python_filepath.parent.glob(f"**/{possible_module_name}.py")
                )
                if not module_paths:
                    continue
                module_path = module_paths[0]
                with open(module_path) as pf:
                    python_code = pf.read()
                source_codes.append(
                    SourceCode(
                        filename=module_path.name,
                        code=omit_middle_code_when_necessary(python_code),
                    )
                )
            return source_codes


def collect_entrypoint_sourcecodes(
    pkg_dirpath: Path, skip_empty_files: bool = True
) -> list[SourceCode]:
    # locate setup.py
    python_setuppy_filepath: Path = min(
        list(pkg_dirpath.glob("**/setup.py")), key=lambda p: len(p.parts)
    )
    # search for __init__.py
    python_initpy_filepaths = list(
        python_setuppy_filepath.parent.glob("**/__init__.py")
    )
    python_initpy_filepath = (
        min(python_initpy_filepaths, key=lambda p: len(p.parts))
        if python_initpy_filepaths
        else None
    )
    python_filepaths = [python_setuppy_filepath] + (
        [python_initpy_filepath] if python_initpy_filepath else []
    )
    # filter out empty files
    if skip_empty_files:
        python_filepaths = list(
            filter(lambda p: open(p).read().strip() != "", python_filepaths)
        )
    return list(
        chain.from_iterable(
            collect_codes_for_pyfile(python_filepath=pf) for pf in python_filepaths
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pkg-dirpath",
        help="path to the python package directory right under which setup.py is located",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--llm-runner",
        help="llm runner to use to execute llm inference",
        choices=["ollama", "sglang"],
        default="ollama",
    )
    parser.add_argument(
        "--low-memory-mode",
        help="use qwen3:4b powered by Ollama for all agents to reduce required memory (at the significant cost of performance)",
        action="store_true",
    )
    args = parser.parse_args()

    # load configuration env vars
    load_dotenv()

    # initialize CHASE
    supervisor_llm, workers_llm, formatter_llm = prepare_llms(
        llm_runner=args.llm_runner, low_memory_mode=args.low_memory_mode
    )
    chase = create_global_agents_graph(
        supervisor_llm=supervisor_llm,
        workers_llm=workers_llm,
        formatter_llm=formatter_llm,
    )

    # start analysis
    final_state: dict[str, Any] = chase.invoke(
        input=DetectorAgentState(
            today_str=datetime.datetime.now().strftime("%B %d, %Y"),
            package_name=args.pkg_dirpath.name,
            source_codes=collect_entrypoint_sourcecodes(pkg_dirpath=args.pkg_dirpath),
        ),
        config={"recursion_limit": 50},
        print_mode="values",
    )

    # save text analysis report and json-formatted analysis report in the package directory
    with open(
        args.pkg_dirpath / "text-final-summary.txt", "w"
    ) as text_final_summary_file:
        text_final_summary_file.write(final_state["final_summary"])
    with open(
        args.pkg_dirpath / "structured-final-summary.json", "w"
    ) as text_final_summary_file:
        text_final_summary_file.write(
            final_state["final_summary_structured"].model_dump_json()
        )
