import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Maestro',
  tagline: 'Autonomous coding agent orchestration for enterprise teams',
  favicon: 'img/favicon.png',

  future: {
    v4: true,
  },

  url: 'https://maestro.frankchan.dev',
  baseUrl: '/',

  organizationName: 'dunkinfrunkin',
  projectName: 'maestro',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],
  clientModules: ['./src/mermaidZoom.js'],

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          path: 'docs',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      defaultMode: 'light',
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'Maestro',
      logo: {
        alt: 'Maestro',
        src: 'img/logo.png',
        width: 32,
        height: 32,
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/philosophy',
          label: 'Philosophy',
          position: 'left',
        },
        {
          to: '/changelog',
          label: 'Changelog',
          position: 'right',
        },
        {
          href: 'https://github.com/dunkinfrunkin/maestro',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'light',
      links: [
        {
          title: 'Source',
          items: [
            {label: 'GitHub', href: 'https://github.com/dunkinfrunkin/maestro'},
            {label: 'Issues', href: 'https://github.com/dunkinfrunkin/maestro/issues'},
            {label: 'Releases', href: 'https://github.com/dunkinfrunkin/maestro/releases'},
          ],
        },
        {
          title: 'Docs',
          items: [
            {label: 'Getting Started', to: '/docs/getting-started'},
            {label: 'Pipeline', to: '/docs/pipeline'},
            {label: 'Agents', to: '/docs/agents'},
            {label: 'Plugins', to: '/docs/plugins'},
          ],
        },
      ],
      copyright: `MIT License \u00b7 \u00a9 ${new Date().getFullYear()} Frank Chan`,
    },
    mermaid: {
      theme: {light: 'base'},
      options: {
        securityLevel: 'loose',
        themeVariables: {
          primaryColor: '#ebe5d9',
          primaryTextColor: '#2c2416',
          primaryBorderColor: '#d4cab8',
          lineColor: '#8a7e6b',
          secondaryColor: '#f5f0e8',
          tertiaryColor: '#f5f0e8',
          fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: '14px',
          nodeBorder: '#d4cab8',
          mainBkg: '#ebe5d9',
          clusterBkg: '#f5f0e8',
          clusterBorder: '#d4cab8',
          edgeLabelBackground: '#f5f0e8',
        },
      },
    },
    prism: {
      theme: prismThemes.dracula,
      additionalLanguages: ['bash', 'python', 'yaml', 'json'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
