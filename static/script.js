document.addEventListener('DOMContentLoaded', function() {
    const orderInput = document.getElementById('orderNumber');
    const customNameInput = document.getElementById('customName');
    const searchBtn = document.getElementById('searchBtn');
    const clearBtn = document.getElementById('clearBtn');
    const includeMapCheckbox = document.getElementById('includeMap');
    const langButtons = document.querySelectorAll('.lang-btn');
    let selectedLanguage = 'he';
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessage = document.getElementById('errorMessage');
    const resultSection = document.getElementById('resultSection');
    const customerName = document.getElementById('customerName');
    const gameName = document.getElementById('gameName');
    const ticketsList = document.getElementById('ticketsList');
    const quickLinksList = document.getElementById('quickLinksList');
    const copyAllLinksBtn = document.getElementById('copyAllLinksBtn');
    const messagePreview = document.getElementById('messagePreview');
    const copyBtn = document.getElementById('copyBtn');
    const whatsappBtn = document.getElementById('whatsappBtn');
    const markSentBtn = document.getElementById('markSentBtn');
    const sentConfirmation = document.getElementById('sentConfirmation');

    let currentMessage = '';
    let currentOrderData = null;
    let currentLinks = [];

    orderInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchOrder();
        }
    });

    searchBtn.addEventListener('click', searchOrder);
    
    clearBtn.addEventListener('click', function() {
        orderInput.value = '';
        customNameInput.value = '';
        hideResult();
        hideError();
        orderInput.focus();
    });

    includeMapCheckbox.addEventListener('change', function() {
        if (currentOrderData) {
            searchOrder();
        }
    });

    langButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            langButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            selectedLanguage = this.dataset.lang;
            if (currentOrderData) {
                searchOrder();
            }
        });
    });

    async function searchOrder() {
        const orderNumber = orderInput.value.trim();
        
        if (!orderNumber) {
            showError('אנא הזן מספר הזמנה');
            return;
        }

        hideError();
        hideResult();
        showLoading();

        try {
            const response = await fetch('/api/search_order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    order_number: orderNumber,
                    custom_name: customNameInput.value.trim(),
                    include_map: includeMapCheckbox.checked,
                    language: selectedLanguage
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'שגיאה בחיפוש');
            }

            currentOrderData = data.order_data;
            displayResult(data);
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoading();
        }
    }

    function displayResult(data) {
        customerName.textContent = data.customer_name;
        
        const alreadySentWarning = document.getElementById('alreadySentWarning');
        if (data.already_sent) {
            alreadySentWarning.classList.remove('hidden');
        } else {
            alreadySentWarning.classList.add('hidden');
        }
        
        if (data.game_name) {
            gameName.textContent = data.game_name;
            gameName.style.display = 'block';
        } else {
            gameName.style.display = 'none';
        }

        ticketsList.innerHTML = '';
        quickLinksList.innerHTML = '';
        currentLinks = [];
        
        data.tickets.forEach((ticket, index) => {
            const ticketDiv = document.createElement('div');
            ticketDiv.className = 'ticket-item';
            ticketDiv.innerHTML = `
                <strong>כרטיס ${index + 1}:</strong>
                סקטור: ${ticket.sector} | שורה: ${ticket.row} | כיסא: ${ticket.seat}
            `;
            ticketsList.appendChild(ticketDiv);
            
            if (ticket.link) {
                currentLinks.push({ url: ticket.link, seat: ticket.seat });
                const linkDiv = document.createElement('div');
                linkDiv.className = 'quick-link-item';
                linkDiv.innerHTML = `
                    <span class="link-label">כרטיס ${index + 1} (כיסא ${ticket.seat}):</span>
                    <input type="text" class="link-input" value="${ticket.link}" readonly onclick="this.select()">
                    <button class="btn btn-small btn-copy-single" data-link="${ticket.link}">העתק</button>
                    <button class="btn btn-small btn-download-single" data-link="${ticket.link}" data-seat="${ticket.seat}">הורד ⬇</button>
                `;
                quickLinksList.appendChild(linkDiv);
            }
        });

        currentMessage = data.message;
        messagePreview.textContent = data.message;

        resultSection.classList.remove('hidden');
    }

    copyBtn.addEventListener('click', function() {
        if (!currentMessage) return;

        navigator.clipboard.writeText(currentMessage).then(() => {
            const originalText = copyBtn.textContent;
            copyBtn.textContent = 'הועתק!';
            copyBtn.style.background = '#28a745';
            
            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.style.background = '';
            }, 2000);
        }).catch(err => {
            const textarea = document.createElement('textarea');
            textarea.value = currentMessage;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            
            copyBtn.textContent = 'הועתק!';
            setTimeout(() => {
                copyBtn.textContent = 'העתק הודעה';
            }, 2000);
        });
    });

    whatsappBtn.addEventListener('click', function() {
        if (!currentMessage) return;

        const encodedMessage = encodeURIComponent(currentMessage);
        const whatsappUrl = `https://web.whatsapp.com/send?text=${encodedMessage}`;
        window.open(whatsappUrl, '_blank');
    });

    markSentBtn.addEventListener('click', async function() {
        if (!currentOrderData || !currentOrderData.row_indices) return;
        
        markSentBtn.disabled = true;
        markSentBtn.textContent = 'מעדכן...';
        
        try {
            const response = await fetch('/api/mark_sent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    row_indices: currentOrderData.row_indices,
                    order_number: currentOrderData.order_number
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'שגיאה בעדכון');
            }
            
            markSentBtn.textContent = 'נשלח! ✓';
            markSentBtn.classList.add('sent');
            sentConfirmation.classList.remove('hidden');
            
        } catch (error) {
            alert(error.message);
            markSentBtn.textContent = 'סמן כנשלח ✓';
            markSentBtn.disabled = false;
        }
    });

    function showLoading() {
        loadingIndicator.classList.remove('hidden');
    }

    function hideLoading() {
        loadingIndicator.classList.add('hidden');
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }

    function hideResult() {
        resultSection.classList.add('hidden');
        currentOrderData = null;
        currentLinks = [];
        markSentBtn.textContent = 'סמן כנשלח ✓';
        markSentBtn.classList.remove('sent');
        markSentBtn.disabled = false;
        sentConfirmation.classList.add('hidden');
    }

    copyAllLinksBtn.addEventListener('click', function() {
        if (currentLinks.length === 0) return;
        
        const allLinks = currentLinks.map(l => l.url).join('\n');
        navigator.clipboard.writeText(allLinks).then(() => {
            const originalText = copyAllLinksBtn.textContent;
            copyAllLinksBtn.textContent = 'הועתק!';
            copyAllLinksBtn.style.background = '#28a745';
            copyAllLinksBtn.style.color = 'white';
            
            setTimeout(() => {
                copyAllLinksBtn.textContent = originalText;
                copyAllLinksBtn.style.background = '';
                copyAllLinksBtn.style.color = '';
            }, 2000);
        });
    });

    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-copy-single')) {
            const link = e.target.dataset.link;
            navigator.clipboard.writeText(link).then(() => {
                const originalText = e.target.textContent;
                e.target.textContent = 'הועתק!';
                e.target.style.background = '#28a745';
                
                setTimeout(() => {
                    e.target.textContent = originalText;
                    e.target.style.background = '';
                }, 1500);
            });
        }
        
        if (e.target.classList.contains('btn-download-single')) {
            const link = e.target.dataset.link;
            const originalText = e.target.textContent;
            
            window.open(link, '_blank');
            
            e.target.textContent = 'נפתח ✓';
            e.target.style.background = '#28a745';
            setTimeout(() => {
                e.target.textContent = originalText;
                e.target.style.background = '';
            }, 2000);
        }
    });

    const downloadAllZipBtn = document.getElementById('downloadAllZipBtn');
    downloadAllZipBtn.addEventListener('click', function() {
        if (currentLinks.length === 0) return;
        
        const originalText = downloadAllZipBtn.textContent;
        
        currentLinks.forEach((ticket, index) => {
            setTimeout(() => {
                window.open(ticket.url, '_blank');
            }, index * 500);
        });
        
        downloadAllZipBtn.textContent = 'נפתחו ✓';
        downloadAllZipBtn.style.background = '#28a745';
        setTimeout(() => {
            downloadAllZipBtn.textContent = originalText;
            downloadAllZipBtn.style.background = '';
        }, 3000);
    });
});
