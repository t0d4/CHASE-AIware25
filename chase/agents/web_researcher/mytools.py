import hashlib
import os
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import magic
import requests
import vt
from bs4 import BeautifulSoup, Comment
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class FetchPackageInfoFromPyPIInput(BaseModel):
    package_name: str = Field(
        description="The name of the PyPI package to fetch information for"
    )
    package_version: str = Field(
        description='MUST be either "latest" (to fetch latest version info) OR a specific version string like "2.28.0", "1.0.0", "0.1.2". '
        'Do NOT use "None", ">3", ">=1.0", or any comparison operators. Only exact version strings like "2.28.0" are accepted.'
    )


class PyPIJSONAPIPackageInfo(BaseModel):
    author: Optional[str]
    author_email: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    version: str
    release_url: str


class PyPIJSONAPIResponse(BaseModel):
    info: PyPIJSONAPIPackageInfo


@tool(args_schema=FetchPackageInfoFromPyPIInput)
def fetch_package_info_from_pypi(
    package_name: str, package_version: str = "latest"
) -> str:
    """Fetch package metadata from PyPI's JSON API.

    **When to use this tool:**
    - To get metadata about a PyPI package (name, version, dependencies, etc.)
    - To investigate package details during malware analysis
    - To check package release dates, authors, and descriptions
    - To verify package existence and availability

    **Input format:**
    - package_name: The exact PyPI package name (e.g., "requests", "numpy")
    - package_version: MUST be "latest" OR a specific version like "2.28.0"
      * Use "latest" to fetch the latest version information
      * Use exact version strings like "2.28.0", "1.0.0", "0.1.2"
      * Do NOT use "None", ">3", ">=1.0", or any comparison operators
      * Only concrete version numbers are accepted

    **Examples:**
    - Latest version: package_name="requests", package_version="latest"
    - Specific version: package_name="requests", package_version="2.28.0"
    - Another specific version: package_name="numpy", package_version="1.24.3"

    **What you get back:**
    - SUCCESS: Complete metadata including package info, description, URLs, etc.
    - FAILURE: Error details if package not found

    **Critical:** This tool provides authoritative package data directly from PyPI.
    **IMPORTANT:** Always use "latest" for the latest version, never use "None" or comparison operators.
    """
    url_without_version = f"https://pypi.org/pypi/{package_name}/json"
    url_with_version = f"https://pypi.org/pypi/{package_name}/{package_version}/json"

    # Handle "latest" or specific version
    url = (
        url_without_version if package_version.lower() == "latest" else url_with_version
    )

    try:
        r = requests.get(url=url, allow_redirects=True, timeout=10)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            if package_version.lower() != "latest":
                # maybe the package itself exists but the specified version is invalid
                try:
                    if requests.get(url_without_version, timeout=10).status_code == 200:
                        return f"FAILED TO FETCH PACKAGE INFO FOR VERSION {package_version}: Package named {package_name} does exist on PyPI, but no version matching {package_version} was found."
                except Exception:
                    pass
            return f"FAILED TO FETCH PACKAGE INFO: Package named {package_name} currently doesn't exist on PyPI."
        return f"FAILED TO FETCH PACKAGE INFO: {type(e).__name__}: {e}."
    except Exception as e:
        return f"FAILED TO FETCH PACKAGE INFO: {type(e).__name__}: {e}."
    else:
        response_model = PyPIJSONAPIResponse.model_validate(r.json())
        return (
            "[Package Author]\n"
            "\n"
            f"{response_model.info.author or ''} {response_model.info.author_email or ''}\n"
            "\n"
            "[Version and Release URL]\n"
            "\n"
            f"Version {response_model.info.version} is released at {response_model.info.release_url}\n"
            "\n"
            "[Package Description]\n"
            "\n"
            "[[Short Summary]]\n"
            "\n"
            f"{response_model.info.summary or 'Not provided'}\n"
            "\n"
            "[[Long Description]]\n"
            "\n"
            f"{(response_model.info.description[:3000] + '... [truncated - remaining content omitted]' if len(response_model.info.description) > 3000 else response_model.info.description) if response_model.info.description else 'Not provided'}\n"
        )


class FetchContentAtURLInput(BaseModel):
    url: str = Field(description="The HTTP or HTTPS URL to fetch content from")


@tool(args_schema=FetchContentAtURLInput)
def fetch_content_at_url(
    url: str,
) -> str:
    """IMMEDIATELY fetch and analyze content from any suspicious URL.

    **When to use this tool:**
    - ANY time you see a URL in the analysis request
    - To investigate C2 servers, payload URLs, or suspicious domains
    - To download and inspect malicious content
    - FIRST STEP for any URL-based investigation

    **Input format:** Full URL with http:// or https://
    **Example:** "https://suspicious-domain.com/malware.js"

    **What you get back:**
    - SUCCESS: Raw text content for analysis
    - FAILURE: Specific error details for forensic reporting

    **Critical:** This tool provides DIRECT evidence - always use it when URLs are mentioned.
    """
    try:
        r = requests.get(url=url, allow_redirects=True, timeout=10)
        r.raise_for_status()
    except Exception as e:
        return f"FAILED TO FETCH CONTENT: {type(e).__name__}: {e}. This request should not be retried."
    else:
        content_type = r.headers.get("Content-Type", "").lower()

        # Text content types that are safe to decode
        text_content_types = [
            "text/",
            "application/json",
            "application/xml",
            "application/javascript",
        ]
        is_text = any(text_type in content_type for text_type in text_content_types)

        # If not recognized as text, treat as binary
        if not is_text:
            return f"CONTENT IS NOT TEXT: {magic.from_buffer(r.content)}"

        try:
            decoded_text = r.text
        except Exception:
            return f"CONTENT IS NOT TEXT: {magic.from_buffer(r.content)}"
        else:
            if "text/html" in content_type:
                try:
                    soup = BeautifulSoup(decoded_text, "html.parser")

                    # Remove script, style, and noscript tags
                    for element_to_remove in soup.find_all(
                        ["script", "style", "noscript"]
                    ):
                        element_to_remove.decompose()

                    # Remove HTML comments
                    for comment in soup.find_all(
                        string=lambda text: isinstance(text, Comment)
                    ):
                        comment.extract()

                    # Get the remaining text content
                    # separator=' ' adds a space between text from different tags, strip=True removes leading/trailing whitespace
                    cleaned_text = soup.get_text(separator=" ", strip=True)

                    # Optional: Further clean up multiple spaces/newlines if desired,
                    # though get_text(strip=True) handles a lot of it.
                    # cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

                    return cleaned_text
                except Exception:
                    # Fallback to returning the original decoded_text if HTML processing fails
                    return decoded_text
            else:
                # If not HTML, but successfully decoded (e.g., JS, CSS, plain text), return the raw decoded text
                return decoded_text


class InspectDomainOrUrlUsingVirusTotalInput(BaseModel):
    domain_or_url: str = Field(
        description="The domain name or full URL to analyze using VirusTotal threat intelligence"
    )


@tool(args_schema=InspectDomainOrUrlUsingVirusTotalInput)
def inspect_domain_or_url_using_virustotal(domain_or_url: str) -> str:
    """COMPREHENSIVE threat intelligence tool using VirusTotal's security database.

    **When to use this tool:**
    - To get reputation data and threat intelligence for domains or URLs
    - To check if URLs/domains are flagged by security vendors
    - To gather detection statistics and categorization information
    - For comprehensive security assessment of web indicators

    **Input format:**
    - Full URL: "https://suspicious-site.com/path"
    - Domain only: "suspicious-site.com"

    **Intelligence you'll discover:**
    - Security vendor detection results and statistics
    - Domain/URL categorization by threat intelligence providers
    - File analysis if URL content is downloadable
    - WHOIS data and registration information
    - Historical analysis data and timestamps

    **Critical:** This tool provides authoritative security intelligence from multiple vendors.
    """

    vt_api_key = os.environ.get("VIRUS_TOTAL_API_KEY")
    if not vt_api_key:
        raise ValueError("VIRUS_TOTAL_API_KEY should be set")

    def is_full_url(maybe_full_url: str) -> bool:
        """
        Determine if the given string is url or just a domain name.

        Args:
            maybe_full_url (str): a string that may be a url.

        Returns:
            bool: True if given str is a "Full URL", False otherwise.
        """
        domain_regex = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$"
        )

        try:
            parsed = urlparse(maybe_full_url)
            if parsed.scheme and parsed.netloc:
                return True

            if domain_regex.match(maybe_full_url):
                return False

        except ValueError:
            raise ValueError(
                f"the given string ({maybe_full_url}) is not a valid url nor a valid domain."
            )

        raise ValueError(
            f"the given string ({maybe_full_url}) is not a valid url nor a valid domain."
        )

    with vt.Client(apikey=vt_api_key) as vt_client:
        try:
            file_info, url_info = None, None
            if is_full_url(domain_or_url):
                try:
                    file_hash = hashlib.sha1(
                        requests.get(url=domain_or_url, timeout=10).content
                    ).hexdigest()
                    file_info = vt_client.get_object("/files/{}", file_hash)
                except Exception:
                    pass
                url_info = vt_client.get_object("/urls/{}", vt.url_id(domain_or_url))
                domain_info = vt_client.get_object(
                    "/domains/{}", urlparse(domain_or_url).netloc
                )
            else:
                domain_info = vt_client.get_object("/domains/{}", domain_or_url)
        except vt.error.APIError as e:
            if e.args[0] == "NotFoundError":
                url_or_domain = "URL" if is_full_url(domain_or_url) else "domain"
                return (
                    f"NOT FOUND IN VIRUSTOTAL: The {url_or_domain} '{domain_or_url}' has no data in VirusTotal's database.\n\n"
                    f"This could mean:\n"
                    f"1. The {url_or_domain} is not yet known to VirusTotal (new/unknown indicator)\n"
                    f"2. There may be a typo in the {url_or_domain} - verify the exact characters from the source code\n\n"
                    f"If you suspect a typo, double-check the original string and retry with the correct value."
                )
            raise
        except Exception:
            raise
        else:
            result_lines = ["# VirusTotal Analysis Report\n"]

            # today's date
            result_lines.append(
                f"Today's Date: {datetime.now().isoformat(timespec='seconds')}\n"
            )

            # File information (if available)
            if file_info is not None:
                result_lines.append("## File Analysis")
                result_lines.append(
                    f"**Last Analysis Date:** {datetime.fromtimestamp(file_info.get('last_analysis_date')).isoformat()}"
                )

                # Format analysis stats
                stats = file_info.get("last_analysis_stats")
                if stats:
                    result_lines.append("**Analysis Stats:**")
                    for key, value in stats.items():
                        result_lines.append(
                            f"- {key.replace('_', ' ').title()}: {value}"
                        )
                result_lines.append("")

            # URL information (if available)
            if url_info is not None:
                result_lines.append("## URL Analysis")
                result_lines.append(
                    f"**Last Analysis Date:** {datetime.fromtimestamp(url_info.get('last_analysis_date')).isoformat()}"
                )

                # Format categories
                categories = url_info.get("categories")
                if categories:
                    result_lines.append("**Categories:**")
                    for provider, classification in categories.items():
                        result_lines.append(f"- {provider}: {classification}")

                # Format analysis stats
                stats = url_info.get("last_analysis_stats")
                if stats:
                    result_lines.append("**Analysis Stats:**")
                    for key, value in stats.items():
                        result_lines.append(
                            f"- {key.replace('_', ' ').title()}: {value}"
                        )
                result_lines.append("")

            # Domain information (always available)
            result_lines.append("## Domain Analysis")

            # Format categories
            categories = domain_info.get("categories")
            if categories:
                result_lines.append("**Categories:**")
                for provider, classification in categories.items():
                    result_lines.append(f"- {provider}: {classification}")

            # Format analysis stats
            stats = domain_info.get("last_analysis_stats")
            if stats:
                result_lines.append("**Analysis Stats:**")
                for key, value in stats.items():
                    result_lines.append(f"- {key.replace('_', ' ').title()}: {value}")

            # Format WHOIS information
            whois_info = domain_info.get("whois")
            if whois_info:
                result_lines.append("**WHOIS Information:**")
                result_lines.append(f"```\n{whois_info}\n```")

            return "\n".join(result_lines)
