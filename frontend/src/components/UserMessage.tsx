interface Props {
  text: string;
}

export default function UserMessage({ text }: Props) {
  return (
    <div className="flex justify-end">
      <div className="max-w-xs lg:max-w-md bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm">
        {text}
      </div>
    </div>
  );
}
