import type { Metadata } from "next";
import Script from "next/script";
import "../styles/global.css";

export const metadata: Metadata = {
  title: "SysLink — CRM",
  description: "CRM de gestão de leads e funil de vendas",
  icons: {
    icon: "/logo.ico",
  },
};

/**
 * Roda antes da primeira pintura: se o usuário salvou o modo claro,
 * aplica data-theme no <html> sem piscar o tema escuro. Só o claro é
 * aplicado aqui — o escuro é o padrão e não precisa de atributo.
 * Mesma chave usada pelo botão da Sidebar.
 */
const THEME_INIT = `(function(){try{if(localStorage.getItem("syslink-theme")==="light"){document.documentElement.dataset.theme="light"}}catch(e){}})();`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // suppressHydrationWarning: o script acima pode setar data-theme
    // antes da hidratação e o servidor não sabe disso.
    <html lang="pt-BR" suppressHydrationWarning>
      <body>
        <Script id="syslink-theme-init" strategy="beforeInteractive">
          {THEME_INIT}
        </Script>
        {children}
      </body>
    </html>
  );
}
