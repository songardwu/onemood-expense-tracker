(function() {
    var vendorInput = document.getElementById('vendor');
    var hintBox = document.getElementById('vendor-hint');
    if (!vendorInput || !hintBox) return;

    var timer = null;

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
})();
