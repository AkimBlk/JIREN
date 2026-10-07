/**
 * Git Setup Modal Handler (Bootstrap 4 / jQuery)
 * Manages form submission, private toggle, and provider detection from URL.
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

    function setTokenPlaceholderVisible(visible) {
      if (!accessTokenInput) return;
      var placeholderSample = accessTokenInput.getAttribute('data-token-placeholder') || '';
      accessTokenInput.placeholder = visible ? placeholderSample : '';
      accessTokenInput.setAttribute('data-token-has-placeholder', visible ? 'true' : 'false');
    }

    function updatePrivateModeState() {
      if (!isPrivateCheckbox || !accessTokenGroup || !accessTokenInput) return;
      var isChecked = isPrivateCheckbox.checked;

      accessTokenGroup.classList.toggle('d-none', !isChecked);
      accessTokenGroup.classList.toggle('is-active', isChecked);
      accessTokenInput.required = isChecked;
      isPrivateCheckbox.setAttribute('aria-expanded', isChecked ? 'true' : 'false');

      if (isChecked && !accessTokenInput.value) {
        setTokenPlaceholderVisible(true);
      }
      if (!isChecked) {
        setTokenPlaceholderVisible(false);
      }
    }

    if (isPrivateCheckbox) {
      isPrivateCheckbox.addEventListener('change', updatePrivateModeState);
    }

    if (accessTokenInput) {
      accessTokenInput.addEventListener('focus', function () {
        setTokenPlaceholderVisible(false);
      });
      accessTokenInput.addEventListener('click', function () {
        setTokenPlaceholderVisible(false);
      });
      accessTokenInput.addEventListener('blur', function () {
        if (!accessTokenInput.value && isPrivateCheckbox && isPrivateCheckbox.checked) {
          setTokenPlaceholderVisible(true);
        }
      });
      accessTokenInput.addEventListener('input', function () {
        if (accessTokenInput.value) {
          setTokenPlaceholderVisible(false);
        }
      });
    }

    updatePrivateModeState();

    var PROVIDER_PATTERNS = { github: /github\.com/i, gitlab: /gitlab\.(com|org)/i, gitea: /gitea\.|codeberg\.org/i };

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

    function showAlert(message, type) {
      alertBox.textContent = message;
      alertBox.className = 'alert alert-' + type;
      alertBox.classList.remove('d-none');
    }

    function hideAlert() {
      alertBox.classList.add('d-none');
    }

    function setLoading(loading) {
      submitBtn.disabled = loading;
      submitText.classList.toggle('d-none', loading);
      submitSpinner.classList.toggle('d-none', !loading);
    }

    var HTTP_STATUS_UNAUTHORIZED = 401;
    var HTTP_STATUS_FORBIDDEN    = 403;
    var HTTP_STATUS_NOT_FOUND    = 404;
    var HTTP_STATUS_CONFLICT     = 409;
    var HTTP_STATUS_BAD_REQUEST  = 400;
    var REDIRECT_DELAY_MS        = 600;

    var ERROR_MESSAGES = {};
    ERROR_MESSAGES[HTTP_STATUS_UNAUTHORIZED] = 'Session expired. Please sign in again.';
    ERROR_MESSAGES[HTTP_STATUS_FORBIDDEN]    = 'Access denied for this project.';
    ERROR_MESSAGES[HTTP_STATUS_NOT_FOUND]    = 'Git repository not found for this project.';
    ERROR_MESSAGES[HTTP_STATUS_CONFLICT]     = 'Repository already configured. Reload the page and edit it.';

    function errorMessageForStatus(httpStatus, rawText, data) {
      if (data && data.error) return data.error;
      if (ERROR_MESSAGES[httpStatus]) return ERROR_MESSAGES[httpStatus];
      if (httpStatus === HTTP_STATUS_BAD_REQUEST && rawText.toLowerCase().indexOf('csrf') !== -1) {
        return 'Security check failed (CSRF). Reload the page and try again.';
      }
      return 'Request failed (' + httpStatus + ').';
    }

    async function submitGitSetupForm(csrfToken) {
      try {
        var response = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          credentials: 'same-origin',
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken.value }
        });
        var contentType = (response.headers.get('content-type') || '').toLowerCase();
        var data    = contentType.indexOf('application/json') !== -1 ? await response.json() : null;
        var rawText = data === null ? await response.text() : '';
        setLoading(false);
        if (!response.ok) {
          showAlert(errorMessageForStatus(response.status, rawText, data), 'danger');
          return;
        }
        if (data && data.success) {
          showAlert(data.message || 'Repository configured.', 'success');
          await new Promise(function (resolve) { setTimeout(resolve, REDIRECT_DELAY_MS); });
          window.location.href = data.redirect_url;
        } else {
          showAlert((data && data.error) || 'An error occurred. Check the form.', 'danger');
        }
      } catch (error) {
        setLoading(false);
        showAlert((error && error.message) || 'Network error. Please try again.', 'danger');
      }
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      hideAlert();
      var csrfToken = form.querySelector('[name=csrfmiddlewaretoken]');
      if (!csrfToken) return;
      setLoading(true);
      submitGitSetupForm(csrfToken);
    });
  });
})();
