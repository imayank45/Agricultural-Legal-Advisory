// Store the summary globally so translateAndSpeak can access it
let currentSummary = "";

document.getElementById("contractForm").addEventListener("submit", async function (event) {
    event.preventDefault();
    const fileInput = document.getElementById("contractFile");
    
    if (fileInput.files.length === 0) {
        alert("Please upload a file.");
        return;
    }

    const formData = new FormData();
    formData.append("contract", fileInput.files[0]);

    const resultsDiv = document.getElementById("results");
    resultsDiv.innerHTML = "<p>Loading...</p>";

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            body: formData
        });
        const result = await response.json();

        if (result.error) {
            resultsDiv.innerHTML = `<p class="error">${result.error}</p>`;
            return;
        }

        // Store the summary for later use
        currentSummary = result.summary;

        resultsDiv.innerHTML = `
            <div class="result-section">
                <h3 onclick="toggleSection('risks')">Risky Clauses <span class="toggle-icon">▼</span></h3>
                <div id="risks" class="content">
                    ${result.risks.map((risk, index) => `
                        <div class="risk-item ${risk.risk === 'SAFE' ? 'safe' : 'risky'}">
                            <p><strong>Clause ${index + 1}:</strong> ${risk.clause}</p>
                            <p><strong>Risk:</strong> ${risk.risk} (Score: ${risk.score.toFixed(4)})</p>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="result-section">
                <h3 onclick="toggleSection('summary')">Summary <span class="toggle-icon">▼</span></h3>
                <div id="summary" class="content">
                    <p>${result.summary}</p>
                </div>
            </div>
        `;
    } catch (error) {
        resultsDiv.innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
});

// Toggle section visibility
function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    const icon = section.previousElementSibling.querySelector(".toggle-icon");
    if (section.style.display === "none") {
        section.style.display = "block";
        icon.textContent = "▼";
    } else {
        section.style.display = "none";
        icon.textContent = "▲";
    }
}

// Translate and play the summary
async function translateAndSpeak() {
    if (!currentSummary) {
        alert("Please analyze a document first to get a summary.");
        return;
    }

    const languageSelect = document.getElementById("languageSelect").value;
    const translatedSummaryDiv = document.getElementById("translatedSummary");
    const audioPlayer = document.getElementById("audioPlayer");

    try {
        const response = await fetch("/translate_and_speak", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ summary: currentSummary, lang: languageSelect }),
        });
        const result = await response.json();

        if (result.error) {
            translatedSummaryDiv.innerHTML = `<p class="error">${result.error}</p>`;
            return;
        }

        // Display translated summary
        translatedSummaryDiv.innerHTML = `<p>${result.translated_summary}</p>`;

        // Update and play audio
        audioPlayer.src = result.audio_file;  // e.g., "static/output.mp3"
        audioPlayer.style.display = "block"; // Make it visible
        audioPlayer.play();                  // Start playback
    } catch (error) {
        translatedSummaryDiv.innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
}