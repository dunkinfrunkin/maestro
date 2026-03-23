import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Maestro',
  tagline: 'Autonomous coding agent orchestration for enterprise teams',
  favicon: 'img/favicon.svg',

  future: {
    v4: true,
  },

  url: 'https://maestro.frankchan.dev',
  baseUrl: '/',

  organizationName: 'dunkinfrunkin',
  projectName: 'maestro',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

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
      defaultMode: 'dark',
      disableSwitch: false,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'Maestro',
      logo: {
        alt: 'Maestro',
        src: 'img/logo.svg',
        width: 28,
        height: 28,
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
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
      style: 'dark',
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
            {label: 'Configuration', to: '/docs/configuration'},
            {label: 'Plugins', to: '/docs/plugins'},
          ],
        },
      ],
      copyright: `MIT License \u00b7 \u00a9 ${new Date().getFullYear()} Frank Chan`,
    },
    prism: {
      theme: prismThemes.oneDark,
      darkTheme: prismThemes.oneDark,
      additionalLanguages: ['bash', 'python', 'yaml', 'json'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
