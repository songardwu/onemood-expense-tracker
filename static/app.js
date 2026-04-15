(function() {
    var vendorInput = document.getElementById('vendor');
    var hintBox = document.getElementById('vendor-hint');
    var bankBox = document.getElementById('bank-info');
    if (!vendorInput || !hintBox) return;

    var timer = null;

    // 廠商相似性比對（即時 debounce）
    vendorInput.addEventListener('input', function() {
        clearTimeout(timer);
        var q = this.value.trim();
        if (q.length < 2) {
            hintBox.style.display = 'none';
            return;
        }
        timer = setTimeout(function() {
            fetch('/api/check-vendor?q=' + encodeURIComponent(q))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.similar && data.similar.length > 0) {
                        hintBox.textContent =
                            '\u7CFB\u7D71\u4E2D\u5DF2\u6709\u76F8\u4F3C\u5EE0\u5546\uFF1A' +
                            data.similar.join('\u3001') +
                            '\u3002\u662F\u5426\u70BA\u540C\u4E00\u5EE0\u5546\uFF1F';
                        hintBox.style.display = 'block';
                    } else {
                        hintBox.style.display = 'none';
                    }
                })
                .catch(function() { hintBox.style.display = 'none'; });
        }, 300);
    });

    // 選定廠商後查詢銀行資訊
    if (bankBox) {
        vendorInput.addEventListener('change', fetchBankInfo);
        vendorInput.addEventListener('blur', fetchBankInfo);

        function fetchBankInfo() {
            var name = vendorInput.value.trim();
            if (!name) { bankBox.style.display = 'none'; return; }
            fetch('/api/vendor-bank?name=' + encodeURIComponent(name))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.bank_name) {
                        bankBox.innerHTML =
                            '\u9280\u884C\uFF1A' + data.bank_name +
                            '\uFF08' + data.bank_code + '\uFF09' +
                            '<br>\u5E33\u865F\uFF1A' + data.account_no +
                            '\u3000\u6236\u540D\uFF1A' + data.account_name;
                        bankBox.style.display = 'block';
                    } else {
                        bankBox.style.display = 'none';
                    }
                })
                .catch(function() { bankBox.style.display = 'none'; });
        }
    }
})();
