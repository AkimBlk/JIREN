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
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken.value
        }
      })
        .then(function (response) {
          var contentType = response.headers.get('content-type') || '';
          var isJson = contentType.toLowerCase().indexOf('application/json') !== -1;
          if (isJson) {
            return response.json().then(function (data) {
              return { response: response, data: data, rawText: '' };
            });
          }
          return response.text().then(function (rawText) {
            return { response: response, data: null, rawText: rawText || '' };
          });
        })
        .then(function (result) {
          var response = result.response;
          var data = result.data;
          var rawText = result.rawText;
          setLoading(false);

          if (!response.ok) {
            var errorMessage = (data && data.error) ? data.error : '';
            if (!errorMessage) {
              if (response.status === 401) {
                errorMessage = 'Session expired. Please sign in again.';
              } else if (response.status === 403) {
                errorMessage = 'Access denied for this project.';
              } else if (response.status === 404) {
                errorMessage = 'Git repository not found for this project.';
              } else if (response.status === 409) {
                errorMessage = 'Repository already configured. Reload the page and edit it.';
              } else if (response.status === 400 && rawText.toLowerCase().indexOf('csrf') !== -1) {
                errorMessage = 'Security check failed (CSRF). Reload the page and try again.';
              } else {
                errorMessage = 'Request failed (' + response.status + ').';
              }
            }
            showAlert(errorMessage, 'danger');
            return;
          }

          if (data && data.success) {
            showAlert(data.message || 'Repository configured.', 'success');
            setTimeout(function () {
              window.location.href = data.redirect_url;
            }, 600);
          } else {
            showAlert((data && data.error) || 'An error occurred. Check the form.', 'danger');
          }
        })
        .catch(function (error) {
          setLoading(false);
          showAlert((error && error.message) || 'Network error. Please try again.', 'danger');
        });
    });
  });
})();
