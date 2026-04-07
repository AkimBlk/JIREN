/**
 * Git Setup Modal Handler (Bootstrap 4 / jQuery)
 * Manages form submission, private toggle, and auto-detect provider from URL.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('git-setup-form');
    var repoUrlInput = document.getElementById('repository-url');
    var repoTypeSelect = document.getElementById('repository-type');
    var isPrivateCheckbox = document.getElementById('is-private');
    var accessTokenGroup = document.getElementById('access-token-group');
    var accessTokenInput = document.getElementById('access-token');
    var alertBox = document.getElementById('git-setup-alert');
    var submitBtn = document.getElementById('git-setup-submit-btn');
    var submitText = document.getElementById('git-setup-submit-text');
    var submitSpinner = document.getElementById('git-setup-submit-spinner');

    if (!form) return;

    /* ── Toggle access token field when "Private" is checked ── */
    if (isPrivateCheckbox) {
      isPrivateCheckbox.addEventListener('change', function () {
        var isChecked = this.checked;
        accessTokenGroup.style.display = isChecked ? 'block' : 'none';
        if (accessTokenInput) {
          accessTokenInput.required = isChecked;
        }
      });
    }

    /* ── Auto-detect provider from pasted URL ── */
    var PROVIDER_PATTERNS = {
      github: /github\.com/i,
      gitlab: /gitlab\.(com|org)/i,
      gitea: /gitea\.|codeberg\.org/i
    };

    if (repoUrlInput) {
      repoUrlInput.addEventListener('input', function () {
        var url = this.value;
        for (var key in PROVIDER_PATTERNS) {
          if (PROVIDER_PATTERNS[key].test(url)) {
            repoTypeSelect.value = key;
            break;
          }
        }
      });
    }

    /* ── Show/hide inline alert ── */
    function showAlert(message, type) {
      alertBox.textContent = message;
      alertBox.className = 'alert alert-' + type;
      alertBox.classList.remove('d-none');
    }
    function hideAlert() {
      alertBox.classList.add('d-none');
    }

    /* ── Toggle submit button loading state ── */
    function setLoading(loading) {
      submitBtn.disabled = loading;
      submitText.classList.toggle('d-none', loading);
      submitSpinner.classList.toggle('d-none', !loading);
    }

    /* ── AJAX form submission ── */
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      hideAlert();

      var formData = new FormData(form);
      var csrfToken = form.querySelector('[name=csrfmiddlewaretoken]');
      if (!csrfToken) return;

      setLoading(true);

      fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken.value
        }
      })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          setLoading(false);
          if (data.success) {
            showAlert(data.message || 'Repository configured.', 'success');
            setTimeout(function () {
              window.location.href = data.redirect_url;
            }, 600);
          } else {
            showAlert(data.error || 'An error occurred. Check the form.', 'danger');
          }
        })
        .catch(function () {
          setLoading(false);
          showAlert('Network error — please try again.', 'danger');
        });
    });
  });
})();
