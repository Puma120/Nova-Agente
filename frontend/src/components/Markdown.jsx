import { marked } from "marked";

marked.setOptions({ breaks: true, gfm: true });

export default function Markdown({ text }) {
  return (
    <div className="md text-[15px]" dangerouslySetInnerHTML={{ __html: marked.parse(text || "") }} />
  );
}
