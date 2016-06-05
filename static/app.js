var secret_key_input = document.getElementById('secret_key_input');
var example_secret_key = document.getElementById('example_secret_key');

if (example_secret_key && secret_key_input) {
  secret_key_input.addEventListener('input', function() {
    example_secret_key.innerHTML = secret_key_input.value;
  });
}
