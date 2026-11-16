const installArea = document.querySelector('#install-area');
const installButton = document.querySelector('#install-app');
const installHelp = document.querySelector('#install-help');
const standaloneMode = window.matchMedia('(display-mode: standalone)');
let installPrompt = null;

function updateInstallState() {
  installArea.hidden = standaloneMode.matches || navigator.standalone === true;
  if (installArea.hidden) installPrompt = null;
}

updateInstallState();
standaloneMode.addEventListener('change', updateInstallState);

window.addEventListener('beforeinstallprompt', event => {
  event.preventDefault();
  if (!installArea.hidden) installPrompt = event;
});

window.addEventListener('appinstalled', () => {
  installPrompt = null;
  installArea.hidden = true;
});

installButton.addEventListener('click', async () => {
  if (installPrompt) {
    const prompt = installPrompt;
    installPrompt = null;
    try {
      await prompt.prompt();
      return;
    } catch {
      // The browser menu is still available if its prompt could not open.
    }
  }
  installHelp.hidden = !installHelp.hidden;
  installButton.setAttribute('aria-expanded', String(!installHelp.hidden));
});
