import ExecutionEnvironment from '@docusaurus/ExecutionEnvironment';

if (ExecutionEnvironment.canUseDOM) {
  let scale = 1;

  function openModal(svgEl) {
    scale = 1;
    const overlay = document.createElement('div');
    overlay.className = 'mermaid-modal-overlay';

    const content = document.createElement('div');
    content.className = 'mermaid-modal-content';

    const close = document.createElement('button');
    close.className = 'mermaid-modal-close';
    close.innerHTML = '&times;';
    close.onclick = () => overlay.remove();

    const controls = document.createElement('div');
    controls.className = 'mermaid-zoom-controls';

    const zoomIn = document.createElement('button');
    zoomIn.textContent = '+';
    zoomIn.onclick = (e) => {
      e.stopPropagation();
      scale = Math.min(scale + 0.25, 3);
      svgClone.style.transform = `scale(${scale})`;
    };

    const zoomOut = document.createElement('button');
    zoomOut.textContent = '−';
    zoomOut.onclick = (e) => {
      e.stopPropagation();
      scale = Math.max(scale - 0.25, 0.5);
      svgClone.style.transform = `scale(${scale})`;
    };

    const reset = document.createElement('button');
    reset.textContent = '⟲';
    reset.onclick = (e) => {
      e.stopPropagation();
      scale = 1;
      svgClone.style.transform = `scale(1)`;
    };

    controls.append(zoomOut, reset, zoomIn);

    const svgClone = svgEl.cloneNode(true);
    svgClone.style.transformOrigin = 'top left';
    svgClone.style.transition = 'transform 0.2s ease';

    content.append(close, svgClone, controls);
    overlay.append(content);

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.remove();
    });

    document.body.append(overlay);
  }

  function attachListeners() {
    document.querySelectorAll('.docusaurus-mermaid-container').forEach((container) => {
      if (container.dataset.zoomAttached) return;
      container.dataset.zoomAttached = 'true';
      container.addEventListener('click', () => {
        const svg = container.querySelector('svg');
        if (svg) openModal(svg);
      });
    });
  }

  // Attach on load and on route changes
  if (document.readyState === 'complete') {
    setTimeout(attachListeners, 500);
  } else {
    window.addEventListener('load', () => setTimeout(attachListeners, 500));
  }

  // Re-attach on SPA navigation
  const observer = new MutationObserver(() => setTimeout(attachListeners, 500));
  observer.observe(document.body, { childList: true, subtree: true });
}

export default {};
