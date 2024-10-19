// Function to send the initial question
function sendQuestion() {
    const button = document.getElementById('submit-button');
    const askAnotherButton = document.getElementById('ask-another');
    const responseContainer = document.getElementById('response-container');
    const responseElement = document.getElementById('response');

    // Validate inputs
    if (!validateForm()) {
        button.innerHTML = 'Submit';
        button.disabled = false;
        return;
    }

    // Show loading spinner and disable the button
    button.innerHTML = '<div class="spinner"></div>';
    button.disabled = true;

    const question = document.getElementById('question').value;
    const name = document.getElementById('name').value;
    const age = document.getElementById('age').value;
    const additional_notes = document.getElementById('additional_notes').value;
    const category = document.querySelector('#category-buttons .selected')?.textContent || '';

    const data = { question, name, age, category, additional_notes };

    fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.ok ? response.json() : Promise.reject('Failed to fetch'))
    .then(data => {
        if (data.response) {
            // Format and display the response
            const formattedResponse = formatResponse(data.response);
            responseElement.innerHTML = `<p><strong>Original question:</strong> ${question}</p>${formattedResponse}`;

        } else {
            responseElement.innerHTML = 'No response received from the server.';
        }

        // Show response and reset the button
        responseContainer.style.display = 'block';
        askAnotherButton.style.display = 'block';
        button.innerHTML = 'Submit';
        button.disabled = false;
        responseContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    })
    .catch(error => {
        responseElement.innerHTML = `Failed to get response: ${error}`;
        button.innerHTML = 'Submit';
        button.disabled = false;
    });
}

// Validation function to check inputs before form submission
function validateForm() {
    const age = document.getElementById('age').value;
    const ageError = document.getElementById('age-error');

    if (age <= 0) {
        ageError.innerHTML = 'Please enter a valid age.';
        return false;
    } else {
        ageError.innerHTML = '';  // Clear error if validation passes
        return true;
    }
}

// Helper function to format API response
function formatResponse(response) {
    return response
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')   // Bold text
        .replace(/### (.*?)(\n|$)/g, '<h3>$1</h3>')         // Headings
        .replace(/- (.*?)(\n|$)/g, '<li>$1</li>')           // Bullet points
        .replace(/\n\n/g, '<br><br>');                      // Line breaks
}

// Event listeners for category buttons
document.querySelectorAll('#category-buttons .category-button').forEach(button => {
    button.addEventListener('click', () => {
        document.querySelectorAll('#category-buttons .category-button').forEach(b => b.classList.remove('selected'));
        button.classList.add('selected');
    });
});
