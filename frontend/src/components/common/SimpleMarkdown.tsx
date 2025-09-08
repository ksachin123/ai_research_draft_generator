import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Typography } from '@mui/material';

interface SimpleMarkdownProps {
  children: string;
  variant?: 'body1' | 'body2';
}

const SimpleMarkdown: React.FC<SimpleMarkdownProps> = ({ children, variant = 'body1' }) => (
  <Typography variant={variant} component="div" sx={{ lineHeight: 1.6 }}>
    <ReactMarkdown>{children}</ReactMarkdown>
  </Typography>
);

export default SimpleMarkdown;