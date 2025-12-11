import React from 'react';

interface MainContentProps {
  children: React.ReactNode;
  className?: string;
  sidebarOpen?: boolean;
}

export const MainContent: React.FC<MainContentProps> = ({
  children,
  className = '',
  sidebarOpen = true
}) => {
  return (
    <main
      className={`h-screen transition-all duration-300 ${className}`}
      style={{
        paddingTop: '4rem',
        paddingLeft: sidebarOpen ? '100px' : '64px',
        paddingRight: '8px',
        paddingBottom: '0px',
        marginLeft: '0px',
        transition: 'padding-left 0.3s ease-in-out'
      }}
    >
      {children}
    </main>
  );
};

export default MainContent;
