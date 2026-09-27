import React, { useState, useEffect, useRef } from 'react';

export default function AgentDashboard() {
  const [saves, setSaves] = useState([]);
  const [selectedSave, setSelectedSave] = useState('');
  const [newSaveNumber, setNewSaveNumber] = useState('');
  const [inputMessage, setInputMessage] = useState('');
  
  
  const [statusLog, setStatusLog] = useState('Select a save file to begin.');
  const [streamedText, setStreamedText] = useState('');
  const [toolResults, setToolResults] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  //const [Confirmation, setConfirmation] = useState(false);
  //const [EditPopup, setEditPopup] = useState([]);

  const socketRef = useRef(null);
  const chatBottomRef = useRef(null);
  const [activeDirectory, setActiveDirectory] = useState('./my_project');
  const [ProjectMode, setProjectMode] = useState(false);
  const inputRef = useRef('');
  const streamedRef = useRef('');
  useEffect(() => { inputRef.current = inputMessage; }, [inputMessage]);
  useEffect(() => { streamedRef.current = streamedText; }, [streamedText]);

  
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, streamedText]);

  
  useEffect(() => {
    fetchSaves();
  }, []);

  const fetchSaves = async () => {
    try {
      const res = await fetch('http://localhost:8000/saves');
      const data = await res.json();
      setSaves(data);
    } catch (err) {
      console.error("Failed fetching directory save logs:", err);
    }
  };
  useEffect(() => {
  return () => {
    if (socketRef.current) {
      console.log("Cleaning up dangling WebSocket connection...");
      socketRef.current.close();
    }
  };
}, []);

  
  const handleDropdownSelection = async (fileName) => {
    if (!fileName) return;

    setSelectedSave(fileName);
    setStatusLog(`Loading ${fileName}...`);


    try {
      const res = await fetch('http://localhost:8000/saves/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'L', value: fileName })
      });
      const data = await res.json();
      
      setStatusLog(`System: ${data.status}`);
      
      // Filter out system instructions 
      const displayableMessages = data.messages.filter(msg => msg.role !== 'system');
      setChatHistory(displayableMessages);
      
    } catch (err) {
      setStatusLog("Error switching session logs.");
      console.error(err);
    }
  };

  const handleCreateNewSave = async () => {
    if (!newSaveNumber.trim()) return;
    setStatusLog(`Generating save${newSaveNumber}.json...`);

    try {
      const res = await fetch('http://localhost:8000/saves/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'N', value: newSaveNumber })
        
      });
      setStatusLog(`Generating save${newSaveNumber} done`)
      const data = await res.json();

      
      setStatusLog(`System: ${data.status}`);
      setSelectedSave(`save${newSaveNumber}.json`);
      setChatHistory([]); 
      setNewSaveNumber('');
      fetchSaves(); 
    } catch (err) {
      console.error(err);
    }
  };

  const handleSummarize = async () => {
    if (!selectedSave) return;
    setStatusLog(`Compiling asynchronous summary file for ${selectedSave}...`);
    try {
      const res = await fetch('http://localhost:8000/saves/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: selectedSave })
      });
      const data = await res.json();
      setStatusLog(`Summary complete: ${data.status}`);
    } catch (err) {
      console.error(err);
    }
  };
  const webmodefunc = async () => {

  try {
        const res = await fetch('http://localhost:8000/mode/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({mode: 'webmode' })
      });
      const data = await res.json();
      setStatusLog(`Summary complete: ${data.status}`);


  }
   catch (err) {
    console.error("Failed handling Electron IPC routing:", err);
    setStatusLog("Error switching to web mode");
  }
};

  const assistantmodefunc = async () => {

  try {
        const res = await fetch('http://localhost:8000/mode/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({mode: 'assistantmode' })
      });
      const data = await res.json();
      setStatusLog(`Summary complete: ${data.status}`);


  }
   catch (err) {
    console.error("Failed handling Electron IPC routing:", err);
    setStatusLog("Error switching to assistant mode");
  }

  }

  
  
  const handleBrowseDirectory = async () => {
  if (!selectedSave) {
    setStatusLog("Please load a save file before setting a project workspace.");
    return;
  }

  try {
    // Electron folder picker
    const chosenPath = await window.electronAPI.openFolderPicker();
    
    if (!chosenPath) {
      setStatusLog("Folder selection was bypassed.");
      return;
    }

    setStatusLog(`Synchronizing workspace path...`);

    
    const res = await fetch('http://localhost:8000/saves/directory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ directory_path: chosenPath, project_mode: true})
    });
    const data = await res.json();
    
    setProjectMode(true);
    setActiveDirectory(chosenPath);
    setStatusLog(`System: ${data.status}`);
    
  } catch (err) {
    console.error("Failed handling native Electron IPC routing loop:", err);
    setStatusLog("Error connecting to desktop IPC bridge.");
  }
};

  const sendMessage = () => {
    if (!inputMessage.trim()) return;

    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      const ws = new WebSocket('ws://localhost:8000/ws/agent');
      socketRef.current = ws;

      ws.onopen = () => executeSend();

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        switch (payload.type) {
          case 'status':
            setStatusLog(payload.data);
            break;
          case 'token':
            setStreamedText((prev) => prev + payload.data);
            break;
          case 'tool_result':
            setToolResults((prev) => [...prev, payload.data]);
            break;
          /*case 'edit_confirmation':
            setEditPopup(payload.data);
            setConfirmation(true)
            break;  */
          case 'turn_complete':
            setIsProcessing(false);
            setStatusLog('Turn finished.');
            
            setChatHistory((prev) => [
              ...prev,
              { role: 'user', content: inputRef.current },
              { role: 'assistant', content: streamedRef.current }
            ]);
            setInputMessage('');
            setStreamedText('');
            break;
          default:
            break;
        }
      };

      ws.onclose = () => {
        setStatusLog('Socket disconnected.');
        setIsProcessing(false);
      };
    } else {
      executeSend();
    }
  };

  const executeSend = () => {
    setIsProcessing(true);
    setStreamedText(''); 
    socketRef.current.send(JSON.stringify({ message: inputMessage }));
  };

  return (
    <div style={{ display: 'flex', gap: '20px', padding: '20px', fontFamily: 'monospace', background: '#121212', color: '#fff', minHeight: '100vh' }}>
      
      
      
      
      <div style={{ width: '30%', borderRight: '1px solid #333', paddingRight: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h3 style={{ marginBottom: '10px' }}> Active Saves</h3>
          


          
        <select 
            value={selectedSave} 
            onChange={(e) => handleDropdownSelection(e.target.value)}
            style={{
              width: '100%',
              padding: '12px',
              background: '#262626',
              color: '#fff',
              border: '1px solid #444',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >

            <option value=""> 
              Load Active Save
            </option>
           
           
            {saves.map((file) => (
              <option key={file} value={file}>
                📁 {file}
              </option>
            ))}
          </select>
        </div>

        <div style={{ background: '#1a1a1a', padding: '15px', borderRadius: '6px', border: '1px solid #262626' }}>
         
          <h4 style={{ marginTop: 0, marginBottom: '10px' }}> Initialize New Session</h4>
          
          <div style={{ display: 'flex', gap: '8px' }}>
          <input 
              type="number" 
              placeholder="e.g. 67"
              value={newSaveNumber} 
              style={{ width: '70px', padding: '8px', background: '#262626', border: '1px solid #444', color: '#fff' }} 
              onChange={(e) => setNewSaveNumber(e.target.value)} 
            />
            <button style={{ flexGrow: 1, background: '#2563eb', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }} onClick={handleCreateNewSave}>
              Create & Swap
              </button>
          </div>
        </div>

        {/* maybe add disabled={!selectedSave} */}
        <button 
            style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '12px', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer' }} 
            onClick={handleBrowseDirectory}
          >
         Browse Local Folder
        </button>
        toggles
        <inline><input type="radio" id="mode1" name="modes" value="value1" onClick={webmodefunc}></input> web app mode</inline>
        <inline><input type="radio" id="mode2" name="modes" value="value2" onClick={assistantmodefunc}></input> assistant mode</inline>
        <inline><h5 style={{color: '#7d7171'}}>select a toggle first and then initiate a new save file and  a file directory to work on</h5></inline>
          {selectedSave && (
          <button 
            style={{ background: '#7c3aed', color: '#fff', border: 'none', padding: '12px', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer' }} 
            onClick={handleSummarize}
          >
            Summarize: {selectedSave} (S)
          </button>
          )}

       <div style={{ marginTop: 'auto', background: '#1a1a1a', padding: '12px', borderRadius: '4px', borderLeft: '4px solid #00ff00' }}>
          <h5 style={{ margin: '0 0 5px 0', color: '#888' }}>TRACKER</h5>
         <div style={{ color: '#00ff00', fontSize: '13px' }}>{statusLog}</div>
        </div>
      </div>

      


      <div style={{ width: '70%', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <h2>chat history</h2>

        


       <div style={{ flexGrow: 1, background: '#1e1e1e', padding: '20px', borderRadius: '6px', height: '450px', overflowY: 'auto', border: '1px solid #333' }}>
          {chatHistory.length === 0 && !streamedText && (
            <div style={{ color: '#666', textAlign: 'center', marginTop: '150px' }}>
                No active chat history. Select a save file or type a prompt to start execution.
            </div>
          )}
          
        
          {chatHistory.map((msg, idx) => (
            <div key={idx} style={{ marginBottom: '15px', lineHeight: '1.5' }}>
              <span style={{ color: msg.role === 'user' ? '#3b82f6' : '#ec4899', fontWeight: 'bold' }}>
                {msg.role === 'user' ? ' USER' : ' AGENT'}:
             
              </span>
              
              <span style={{ marginLeft: '8px', whiteSpace: 'pre-wrap' }}>{msg.content}</span>
            </div>
          ))}
          



          {streamedText && (
            <div style={{ marginBottom: '15px', lineHeight: '1.5' }}>
            <span style={{ color: '#ec4899', fontWeight: 'bold' }}> AGENT (Streaming...):</span>
              <span style={{ marginLeft: '8px', color: '#a7f3d0', whiteSpace: 'pre-wrap' }}>{streamedText}</span>
            </div>
          )}
          <div ref={chatBottomRef} />
        </div>

       


        <div style={{ background: '#181019', padding: '12px', maxHeight: '140px', overflowY: 'auto', borderRadius: '6px', border: '1px solid #4a1d4b', fontSize: '12px' }}>
          <div style={{ color: '#d8b4fe', fontWeight: 'bold', marginBottom: '5px' }}> tools used:</div>
          {toolResults.length === 0 && <span style={{ color: '#555' }}>No active environment hooks executed yet.</span>}
          {toolResults.map((tr, idx) => (
            <div key={idx} style={{ marginTop: '5px', paddingBottom: '5px', borderBottom: '1px dashed #3b143c' }}>
              <span style={{ color: '#f472b6' }}>[{tr.tool}]</span> → <span style={{ color: '#93c5fd' }}>{JSON.stringify(tr.result)}</span>
            </div>
          ))}
        </div>

        

        
        <div style={{ display: 'flex', gap: '10px' }}>
          <input 
            type="text" 
            placeholder={selectedSave ? "type here..." : " Please select a save file from the dropdown left before chatting."} 
            value={inputMessage} 
            disabled={isProcessing || !selectedSave}
            style={{ flexGrow: 1, padding: '14px', background: '#262626', border: '1px solid #444', color: '#fff', borderRadius: '4px' }} 
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
           />
          <button 
            style={{ padding: '0 25px', cursor: 'pointer', background: '#059669', border: 'none', color: '#fff', borderRadius: '4px', fontWeight: 'bold' }} 
            disabled={isProcessing || !selectedSave} 
            onClick={sendMessage}
          >
            {isProcessing ? 'Thinking...' : 'Execute'}
          </button>
        </div>
      </div>
          {/*<div
          style={{ display: 'flex', gap: '10px', flex: '1 1 0' }}
          disabled={Confirmation}
          ><span>{JSON.stringify(EditPopup)}</span>
          </div>*/}
    </div>
  );
}